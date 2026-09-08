from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.pdf_fixtures import TWO_PAGE_PDF

from cited_rag.adapters.chunking.page_window import PageWindowChunker
from cited_rag.adapters.embedding.hashing import HashEmbeddingProvider
from cited_rag.adapters.parser.pypdf import PypdfDocumentParser
from cited_rag.adapters.persistence.postgres.uow import PostgresUnitOfWork
from cited_rag.adapters.retrieval.qdrant import QdrantRetrievalStore
from cited_rag.adapters.sparse.lexical import LexicalSparseEncoder
from cited_rag.application.ingestion import process_ingestion_job
from cited_rag.application.retrieval import ReciprocalRankFusion, retrieve_hybrid
from cited_rag.config import Settings
from cited_rag.domain.chunking import ChunkingConfig
from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.enums import DocumentVersionStatus
from cited_rag.main import create_app

pytestmark = [pytest.mark.postgres, pytest.mark.qdrant]

AUTH = {"Authorization": "Bearer test-placeholder-key"}


@pytest.fixture
def client(migrated_database: str, tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        _env_file=None,
        environment="test",
        api_key="test-placeholder-key",
        database_url=migrated_database,
        local_storage_path=str(tmp_path / "objects"),
        max_upload_bytes=1024 * 1024,
        parser_backend="pypdf",
        embedding_dimension=8,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def store(qdrant_url: str) -> AsyncIterator[QdrantRetrievalStore]:
    retrieval = QdrantRetrievalStore(url=qdrant_url, collection_name=f"cited_rag_{uuid4().hex}")
    try:
        yield retrieval
    finally:
        await retrieval.close()


def _uow(session_factory: async_sessionmaker) -> PostgresUnitOfWork:
    return PostgresUnitOfWork(session_factory)


@pytest.mark.asyncio
async def test_hybrid_search_is_collection_and_version_scoped(
    client: TestClient,
    uow_factory: async_sessionmaker,
    store: QdrantRetrievalStore,
) -> None:
    collection = client.post("/v1/collections", json={"name": "hybrid"}, headers=AUTH)
    assert collection.status_code == 201
    collection_id = UUID(collection.json()["collection_id"])
    uploaded = client.post(
        f"/v1/collections/{collection_id}/documents",
        headers=AUTH,
        files={"file": ("policy.pdf", TWO_PAGE_PDF, "application/pdf")},
    )
    assert uploaded.status_code == 202
    version_id = UUID(uploaded.json()["document_version_id"])
    embedder = HashEmbeddingProvider(dimension=8)
    encoder = LexicalSparseEncoder()
    async with _uow(uow_factory) as uow:
        outcome = await process_ingestion_job(
            uow,
            document_version_id=version_id,
            storage=client.app.state.storage,
            parser=PypdfDocumentParser(),
            chunker=PageWindowChunker(ChunkingConfig(target_chars=1200, overlap_chars=200)),
            embedding_provider=embedder,
            retrieval_store=store,
            embedding_config=EmbeddingConfig(dimension=8, batch_size=8, index_version="idx-test"),
            sparse_encoder=encoder,
        )
        version = await uow.versions.get(version_id)
        chunks = await uow.chunks.list_by_version(version_id)
    assert outcome == "processed"
    assert version is not None
    assert version.ingestion_status is DocumentVersionStatus.READY
    fused = await retrieve_hybrid(
        chunks[0].text[:40],
        embedder=embedder,
        encoder=encoder,
        store=store,
        chunks=chunks,
        collection_id=collection_id,
        document_version_ids=[version_id],
        top_k=5,
        fusion=ReciprocalRankFusion(k=60),
        fused_top_k=5,
    )
    assert fused
    assert {item.chunk_id for item in fused} <= {chunk.id for chunk in chunks}
    assert all(item.collection_id == collection_id for item in fused)
    outsider = await retrieve_hybrid(
        chunks[0].text[:40],
        embedder=embedder,
        encoder=encoder,
        store=store,
        chunks=chunks,
        collection_id=uuid4(),
        document_version_ids=[version_id],
        top_k=5,
        fusion=ReciprocalRankFusion(k=60),
        fused_top_k=5,
    )
    assert outsider == []
