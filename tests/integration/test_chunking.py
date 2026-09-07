from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.pdf_fixtures import TWO_PAGE_PDF, make_text_pdf

from cited_rag.adapters.chunking.page_window import PageWindowChunker
from cited_rag.adapters.embedding.hashing import HashEmbeddingProvider
from cited_rag.adapters.parser.pypdf import PypdfDocumentParser
from cited_rag.adapters.persistence.postgres.uow import PostgresUnitOfWork
from cited_rag.adapters.retrieval.memory import MemoryRetrievalStore
from cited_rag.application.ingestion import process_ingestion_job
from cited_rag.config import Settings
from cited_rag.domain.chunking import ChunkingConfig
from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.enums import DocumentVersionStatus
from cited_rag.main import create_app

pytestmark = pytest.mark.postgres

AUTH = {"Authorization": "Bearer test-placeholder-key"}
LONG_PAGE_PDF = make_text_pdf([("lorem " * 80).strip()])


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
        chunk_target_chars=40,
        chunk_overlap_chars=8,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def _upload(client: TestClient, pdf: bytes) -> UUID:
    collection = client.post("/v1/collections", json={"name": "chunks"}, headers=AUTH)
    assert collection.status_code == 201
    collection_id = collection.json()["collection_id"]
    uploaded = client.post(
        f"/v1/collections/{collection_id}/documents",
        headers=AUTH,
        files={"file": ("policy.pdf", pdf, "application/pdf")},
    )
    assert uploaded.status_code == 202
    return UUID(uploaded.json()["document_version_id"])


def _uow(session_factory: async_sessionmaker) -> PostgresUnitOfWork:
    return PostgresUnitOfWork(session_factory)


async def _process(
    client: TestClient,
    uow_factory: async_sessionmaker,
    version_id: UUID,
    *,
    target: int = 40,
    overlap: int = 8,
) -> str:
    async with _uow(uow_factory) as uow:
        return await process_ingestion_job(
            uow,
            document_version_id=version_id,
            storage=client.app.state.storage,
            parser=PypdfDocumentParser(),
            chunker=PageWindowChunker(ChunkingConfig(target_chars=target, overlap_chars=overlap)),
            embedding_provider=HashEmbeddingProvider(dimension=8),
            retrieval_store=MemoryRetrievalStore(),
            embedding_config=EmbeddingConfig(dimension=8, batch_size=8),
        )


@pytest.mark.asyncio
async def test_ingestion_persists_chunks_without_ready(
    client: TestClient, uow_factory: async_sessionmaker
) -> None:
    version_id = _upload(client, TWO_PAGE_PDF)
    outcome = await _process(client, uow_factory, version_id, target=1200, overlap=200)
    assert outcome == "processed"
    async with _uow(uow_factory) as uow:
        version = await uow.versions.get(version_id)
        chunks = await uow.chunks.list_by_version(version_id)
    assert version is not None
    assert version.ingestion_status is DocumentVersionStatus.PROCESSING
    assert version.ready_at is None
    assert [c.page_start for c in chunks] == [1, 2]
    assert [c.chunk_order for c in chunks] == [0, 1]
    assert "alpha-page-one" in chunks[0].text
    assert "beta-page-two" in chunks[1].text
    assert chunks[0].id.version == 5
    assert version.chunking_config == {
        "strategy": "page_char_split_v1",
        "target_chars": 1200,
        "overlap_chars": 200,
    }


@pytest.mark.asyncio
async def test_long_page_chunking_is_reproducible(
    client: TestClient, uow_factory: async_sessionmaker
) -> None:
    version_id = _upload(client, LONG_PAGE_PDF)
    await _process(client, uow_factory, version_id)
    async with _uow(uow_factory) as uow:
        first = await uow.chunks.list_by_version(version_id)
    assert len(first) >= 2
    assert all(c.page_start == c.page_end == 1 for c in first)
    second_outcome = await _process(client, uow_factory, version_id)
    assert second_outcome == "duplicate"
    async with _uow(uow_factory) as uow:
        again = await uow.chunks.list_by_version(version_id)
    assert [c.id for c in again] == [c.id for c in first]


@pytest.mark.asyncio
async def test_parse_path_requires_configured_chunker(
    client: TestClient, uow_factory: async_sessionmaker
) -> None:
    version_id = _upload(client, TWO_PAGE_PDF)
    async with _uow(uow_factory) as uow:
        outcome = await process_ingestion_job(
            uow,
            document_version_id=version_id,
            storage=client.app.state.storage,
            parser=PypdfDocumentParser(),
        )
        version = await uow.versions.get(version_id)
    assert outcome == "failed"
    assert version is not None
    assert version.failure_message == "ingestion chunker is not configured"


@pytest.mark.asyncio
async def test_parse_path_requires_configured_dense_indexer(
    client: TestClient, uow_factory: async_sessionmaker
) -> None:
    version_id = _upload(client, TWO_PAGE_PDF)
    async with _uow(uow_factory) as uow:
        outcome = await process_ingestion_job(
            uow,
            document_version_id=version_id,
            storage=client.app.state.storage,
            parser=PypdfDocumentParser(),
            chunker=PageWindowChunker(),
        )
        version = await uow.versions.get(version_id)
    assert outcome == "failed"
    assert version is not None
    assert version.failure_message == "ingestion dense indexer is not configured"
