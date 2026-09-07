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
from cited_rag.application.ingestion import process_ingestion_job
from cited_rag.config import Settings
from cited_rag.domain.chunking import ChunkingConfig
from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.enums import DocumentVersionStatus
from cited_rag.domain.indexing import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME
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


def _upload(client: TestClient) -> UUID:
    collection = client.post("/v1/collections", json={"name": "dense"}, headers=AUTH)
    assert collection.status_code == 201
    collection_id = collection.json()["collection_id"]
    uploaded = client.post(
        f"/v1/collections/{collection_id}/documents",
        headers=AUTH,
        files={"file": ("policy.pdf", TWO_PAGE_PDF, "application/pdf")},
    )
    assert uploaded.status_code == 202
    return UUID(uploaded.json()["document_version_id"])


@pytest.mark.asyncio
async def test_ingestion_upserts_dense_points_without_ready(
    client: TestClient,
    uow_factory: async_sessionmaker,
    store: QdrantRetrievalStore,
) -> None:
    version_id = _upload(client)
    embedder = HashEmbeddingProvider(dimension=8)
    config = EmbeddingConfig(dimension=8, batch_size=8, index_version="idx-test")
    async with _uow(uow_factory) as uow:
        outcome = await process_ingestion_job(
            uow,
            document_version_id=version_id,
            storage=client.app.state.storage,
            parser=PypdfDocumentParser(),
            chunker=PageWindowChunker(ChunkingConfig(target_chars=1200, overlap_chars=200)),
            embedding_provider=embedder,
            retrieval_store=store,
            embedding_config=config,
        )
        version = await uow.versions.get(version_id)
        chunks = await uow.chunks.list_by_version(version_id)
    assert outcome == "processed"
    assert version is not None
    assert version.ingestion_status is DocumentVersionStatus.PROCESSING
    assert version.ready_at is None
    assert store.vector_names == {DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME}
    assert len(chunks) == 2
    first = await store.get_point(chunks[0].id)
    assert first is not None
    assert first.point_id == chunks[0].id
    assert first.payload["collection_id"] == str(version.collection_id)
    assert first.payload["document_version_id"] == str(version.id)
    assert "text" not in first.payload
    assert DENSE_VECTOR_NAME in first.vectors
    assert SPARSE_VECTOR_NAME not in first.vectors
    filtered = await store.scroll_collection(collection_id=version.collection_id)
    assert {point.point_id for point in filtered} == {chunk.id for chunk in chunks}

    async with _uow(uow_factory) as uow:
        again = await process_ingestion_job(
            uow,
            document_version_id=version_id,
            storage=client.app.state.storage,
            parser=PypdfDocumentParser(),
            chunker=PageWindowChunker(ChunkingConfig(target_chars=1200, overlap_chars=200)),
            embedding_provider=embedder,
            retrieval_store=store,
            embedding_config=config,
        )
    assert again == "duplicate"
    replayed = await store.get_point(chunks[0].id)
    assert replayed is not None
    assert replayed.point_id == chunks[0].id
