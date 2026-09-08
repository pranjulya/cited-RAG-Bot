from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from cited_rag.adapters.persistence.postgres.uow import PostgresUnitOfWork
from cited_rag.application.ingestion import process_ingestion_job
from cited_rag.config import Settings
from cited_rag.domain.enums import DocumentVersionStatus, IngestionJobStatus
from cited_rag.domain.exceptions import PermanentIngestionError, TransientIngestionError
from cited_rag.main import create_app

pytestmark = pytest.mark.postgres

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
AUTH = {"Authorization": "Bearer test-placeholder-key"}


async def _noop(_uow: object, _version: object) -> None:
    return None


@pytest.fixture
def client(migrated_database: str, tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        _env_file=None,
        environment="test",
        api_key="test-placeholder-key",
        database_url=migrated_database,
        local_storage_path=str(tmp_path / "objects"),
        max_upload_bytes=1024,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def _upload(client: TestClient) -> UUID:
    collection = client.post("/v1/collections", json={"name": "jobs"}, headers=AUTH)
    assert collection.status_code == 201
    collection_id = collection.json()["collection_id"]
    uploaded = client.post(
        f"/v1/collections/{collection_id}/documents",
        headers=AUTH,
        files={"file": ("policy.pdf", MINIMAL_PDF, "application/pdf")},
    )
    assert uploaded.status_code == 202
    assert uploaded.json()["status"] == "QUEUED"
    return UUID(uploaded.json()["document_version_id"])


def _uow(session_factory: async_sessionmaker) -> PostgresUnitOfWork:
    return PostgresUnitOfWork(session_factory)


@pytest.mark.asyncio
async def test_enqueue_and_worker_claims_processing(
    client: TestClient, uow_factory: async_sessionmaker
) -> None:
    version_id = _upload(client)
    async with _uow(uow_factory) as uow:
        outcome = await process_ingestion_job(uow, document_version_id=version_id, pipeline=_noop)
        version = await uow.versions.get(version_id)
        job = await uow.ingestion_jobs.get_by_version(version_id)
    assert outcome == "processed"
    assert version is not None
    assert version.ingestion_status is DocumentVersionStatus.PROCESSING
    assert job is not None
    assert job.status is IngestionJobStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_duplicate_delivery_is_idempotent(
    client: TestClient, uow_factory: async_sessionmaker
) -> None:
    version_id = _upload(client)
    async with _uow(uow_factory) as uow:
        first = await process_ingestion_job(uow, document_version_id=version_id, pipeline=_noop)
    async with _uow(uow_factory) as uow:
        second = await process_ingestion_job(uow, document_version_id=version_id, pipeline=_noop)
        version = await uow.versions.get(version_id)
    assert first == "processed"
    assert second == "duplicate"
    assert version is not None
    assert version.ingestion_status is DocumentVersionStatus.PROCESSING


@pytest.mark.asyncio
async def test_transient_failure_retries_then_succeeds(
    client: TestClient, uow_factory: async_sessionmaker
) -> None:
    version_id = _upload(client)
    attempts = {"n": 0}

    async def flaky(_uow: object, _version: object) -> None:
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise TransientIngestionError("redis blip")

    async with _uow(uow_factory) as uow:
        first = await process_ingestion_job(
            uow,
            document_version_id=version_id,
            max_attempts=3,
            lease_seconds=0,
            pipeline=flaky,
        )
    assert first == "retry"
    async with _uow(uow_factory) as uow:
        outcome = await process_ingestion_job(
            uow,
            document_version_id=version_id,
            max_attempts=3,
            lease_seconds=0,
            pipeline=flaky,
        )
        version = await uow.versions.get(version_id)
        job = await uow.ingestion_jobs.get_by_version(version_id)
    assert outcome == "processed"
    assert attempts["n"] == 2
    assert version is not None
    assert version.ingestion_status is DocumentVersionStatus.PROCESSING
    assert job is not None
    assert job.status is IngestionJobStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_retry_exhaustion_marks_failed(
    client: TestClient, uow_factory: async_sessionmaker
) -> None:
    version_id = _upload(client)

    async def always_transient(_uow: object, _version: object) -> None:
        raise TransientIngestionError("db timeout")

    outcomes: list[str] = []
    for _ in range(3):
        async with _uow(uow_factory) as uow:
            outcomes.append(
                await process_ingestion_job(
                    uow,
                    document_version_id=version_id,
                    max_attempts=3,
                    lease_seconds=0,
                    pipeline=always_transient,
                )
            )
    assert outcomes[-1] == "failed"
    async with _uow(uow_factory) as uow:
        version = await uow.versions.get(version_id)
        job = await uow.ingestion_jobs.get_by_version(version_id)
    assert version is not None
    assert version.ingestion_status is DocumentVersionStatus.FAILED
    assert job is not None
    assert job.status is IngestionJobStatus.FAILED


@pytest.mark.asyncio
async def test_permanent_failure_marks_failed(
    client: TestClient, uow_factory: async_sessionmaker
) -> None:
    version_id = _upload(client)

    async def boom(_uow: object, _version: object) -> None:
        raise PermanentIngestionError("source_missing")

    async with _uow(uow_factory) as uow:
        outcome = await process_ingestion_job(uow, document_version_id=version_id, pipeline=boom)
        version = await uow.versions.get(version_id)
    assert outcome == "failed"
    assert version is not None
    assert version.ingestion_status is DocumentVersionStatus.FAILED
    assert version.failure_code == "INGESTION_FAILED"


@pytest.mark.asyncio
async def test_ready_redelivery_is_duplicate(
    client: TestClient, uow_factory: async_sessionmaker
) -> None:
    version_id = _upload(client)
    async with _uow(uow_factory) as uow:
        await process_ingestion_job(uow, document_version_id=version_id, pipeline=_noop)
        version = await uow.versions.get(version_id)
        assert version is not None
        await uow.versions.transition(
            version.id, DocumentVersionStatus.PROCESSING, DocumentVersionStatus.READY
        )
        await uow.commit()
    async with _uow(uow_factory) as uow:
        outcome = await process_ingestion_job(uow, document_version_id=version_id)
        version = await uow.versions.get(version_id)
    assert outcome == "duplicate"
    assert version is not None
    assert version.ingestion_status is DocumentVersionStatus.READY


@pytest.mark.asyncio
async def test_crash_restart_reclaims_expired_lease(
    client: TestClient, uow_factory: async_sessionmaker
) -> None:
    version_id = _upload(client)

    async def crash(_uow: object, _version: object) -> None:
        raise TransientIngestionError("worker killed")

    async with _uow(uow_factory) as uow:
        crashed = await process_ingestion_job(
            uow, document_version_id=version_id, lease_seconds=0, pipeline=crash
        )
    assert crashed == "retry"
    async with _uow(uow_factory) as uow:
        outcome = await process_ingestion_job(
            uow, document_version_id=version_id, lease_seconds=0, pipeline=_noop
        )
        version = await uow.versions.get(version_id)
        job = await uow.ingestion_jobs.get_by_version(version_id)
    assert outcome == "processed"
    assert version is not None
    assert version.ingestion_status is DocumentVersionStatus.PROCESSING
    assert job is not None
    assert job.status is IngestionJobStatus.SUCCEEDED
    assert job.attempt_count >= 2


def test_upload_enqueues_a_wakeup(client: TestClient) -> None:
    _upload(client)
    queue = client.app.state.queue
    jobs = getattr(queue, "jobs", None)
    if jobs is not None:
        assert len(jobs) == 1
