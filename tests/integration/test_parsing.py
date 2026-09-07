from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.pdf_fixtures import CORRUPT_PDF, TWO_PAGE_PDF, make_blank_pdf, make_password_pdf

from cited_rag.adapters.chunking.page_window import PageWindowChunker
from cited_rag.adapters.embedding.hashing import HashEmbeddingProvider
from cited_rag.adapters.parser.pypdf import PypdfDocumentParser
from cited_rag.adapters.persistence.postgres.uow import PostgresUnitOfWork
from cited_rag.adapters.retrieval.memory import MemoryRetrievalStore
from cited_rag.application.ingestion import process_ingestion_job
from cited_rag.config import Settings
from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.enums import DocumentVersionStatus, IngestionJobStatus
from cited_rag.main import create_app

pytestmark = pytest.mark.postgres

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
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def _upload(client: TestClient, pdf: bytes, name: str = "policy.pdf") -> UUID:
    collection = client.post("/v1/collections", json={"name": "parse"}, headers=AUTH)
    assert collection.status_code == 201
    collection_id = collection.json()["collection_id"]
    uploaded = client.post(
        f"/v1/collections/{collection_id}/documents",
        headers=AUTH,
        files={"file": (name, pdf, "application/pdf")},
    )
    assert uploaded.status_code == 202
    return UUID(uploaded.json()["document_version_id"])


def _uow(session_factory: async_sessionmaker) -> PostgresUnitOfWork:
    return PostgresUnitOfWork(session_factory)


async def _process(client: TestClient, uow_factory: async_sessionmaker, version_id: UUID) -> str:
    parser = PypdfDocumentParser()
    storage = client.app.state.storage
    async with _uow(uow_factory) as uow:
        return await process_ingestion_job(
            uow,
            document_version_id=version_id,
            storage=storage,
            parser=parser,
            chunker=PageWindowChunker(),
            embedding_provider=HashEmbeddingProvider(dimension=8),
            retrieval_store=MemoryRetrievalStore(),
            embedding_config=EmbeddingConfig(dimension=8, batch_size=8),
        )


@pytest.mark.asyncio
async def test_worker_persists_page_order_and_stays_processing(
    client: TestClient, uow_factory: async_sessionmaker
) -> None:
    version_id = _upload(client, TWO_PAGE_PDF)
    outcome = await _process(client, uow_factory, version_id)
    assert outcome == "processed"
    async with _uow(uow_factory) as uow:
        version = await uow.versions.get(version_id)
        pages = await uow.pages.list_by_version(version_id)
    assert version is not None
    assert version.ingestion_status is DocumentVersionStatus.PROCESSING
    assert version.page_count == 2
    assert version.ready_at is None
    assert [page.page_number for page in pages] == [1, 2]
    assert pages[0].normalized_text is not None and "alpha-page-one" in pages[0].normalized_text
    assert pages[1].normalized_text is not None and "beta-page-two" in pages[1].normalized_text
    assert pages[0].extraction_metadata is not None
    assert pages[0].extraction_metadata["parser"] == "pypdf"


@pytest.mark.asyncio
async def test_duplicate_parse_does_not_duplicate_pages(
    client: TestClient, uow_factory: async_sessionmaker
) -> None:
    version_id = _upload(client, TWO_PAGE_PDF)
    first = await _process(client, uow_factory, version_id)
    second = await _process(client, uow_factory, version_id)
    async with _uow(uow_factory) as uow:
        pages = await uow.pages.list_by_version(version_id)
    assert first == "processed"
    assert second == "duplicate"
    assert len(pages) == 2


@pytest.mark.asyncio
async def test_corrupt_pdf_fails_permanently(
    client: TestClient, uow_factory: async_sessionmaker
) -> None:
    version_id = _upload(client, CORRUPT_PDF, name="broken.pdf")
    outcome = await _process(client, uow_factory, version_id)
    assert outcome == "failed"
    async with _uow(uow_factory) as uow:
        version = await uow.versions.get(version_id)
        pages = await uow.pages.list_by_version(version_id)
        job = await uow.ingestion_jobs.get_by_version(version_id)
    assert version is not None
    assert version.ingestion_status is DocumentVersionStatus.FAILED
    assert version.failure_code == "PDF_PARSE_FAILED"
    assert pages == []
    assert job is not None
    assert job.status is IngestionJobStatus.FAILED


@pytest.mark.asyncio
async def test_password_pdf_fails_explicitly(
    client: TestClient, uow_factory: async_sessionmaker
) -> None:
    version_id = _upload(client, make_password_pdf(), name="locked.pdf")
    outcome = await _process(client, uow_factory, version_id)
    assert outcome == "failed"
    async with _uow(uow_factory) as uow:
        version = await uow.versions.get(version_id)
    assert version is not None
    assert version.failure_code == "PDF_PASSWORD_PROTECTED"


@pytest.mark.asyncio
async def test_empty_extraction_is_unsupported(
    client: TestClient, uow_factory: async_sessionmaker
) -> None:
    version_id = _upload(client, make_blank_pdf(), name="blank.pdf")
    outcome = await _process(client, uow_factory, version_id)
    assert outcome == "failed"
    async with _uow(uow_factory) as uow:
        version = await uow.versions.get(version_id)
        pages = await uow.pages.list_by_version(version_id)
    assert version is not None
    assert version.failure_code == "PDF_UNSUPPORTED"
    assert pages == []
