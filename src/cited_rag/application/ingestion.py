from __future__ import annotations

import logging
from dataclasses import replace
from datetime import timedelta
from uuid import UUID

from cited_rag.domain.clock import utc_now
from cited_rag.domain.enums import DocumentVersionStatus, IngestionJobStatus
from cited_rag.domain.exceptions import (
    InvalidLifecycleTransitionError,
    OptimisticConcurrencyError,
    PermanentIngestionError,
    TransientIngestionError,
)
from cited_rag.domain.models.ingestion import IngestionJob
from cited_rag.ports.repositories import UnitOfWork

logger = logging.getLogger("cited_rag.ingestion")

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_LEASE_SECONDS = 30


async def process_ingestion_job(
    uow: UnitOfWork,
    *,
    document_version_id: UUID,
    correlation_id: str | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    pipeline: object | None = None,
) -> str:
    """Claim a version, run Phase 03 stub stages, never mark READY.

    `pipeline` is an optional callable `async (uow, version) -> None` used by tests
    to inject transient/permanent failures. Production uses the no-op stub.
    """
    extra = {"correlation_id": correlation_id or "-"}
    version = await uow.versions.get(document_version_id)
    if version is None:
        raise PermanentIngestionError("document version not found")

    if version.ingestion_status in {
        DocumentVersionStatus.READY,
        DocumentVersionStatus.DELETING,
        DocumentVersionStatus.DELETED,
    }:
        logger.info("skip ingestion for terminal version", extra=extra)
        return "skipped"

    job = await uow.ingestion_jobs.get_by_version(document_version_id)
    now = utc_now()
    if job is None:
        job = IngestionJob(
            document_version_id=document_version_id,
            correlation_id=correlation_id,
        )
        await uow.ingestion_jobs.add(job)

    if (
        job.status is IngestionJobStatus.RUNNING
        and job.updated_at + timedelta(seconds=lease_seconds) > now
    ):
        logger.info("lease held; skip duplicate delivery", extra=extra)
        return "leased"

    if job.status is IngestionJobStatus.SUCCEEDED and (
        version.ingestion_status is DocumentVersionStatus.PROCESSING
    ):
        logger.info("already processed; skip duplicate delivery", extra=extra)
        return "duplicate"

    if job.attempt_count >= max_attempts:
        await _fail_permanent(uow, version.id, job, "retry_exhausted")
        return "failed"

    if version.ingestion_status is DocumentVersionStatus.UPLOADED:
        version = await uow.versions.transition(
            version.id, DocumentVersionStatus.UPLOADED, DocumentVersionStatus.QUEUED
        )
    if version.ingestion_status is DocumentVersionStatus.QUEUED:
        try:
            version = await uow.versions.transition(
                version.id, DocumentVersionStatus.QUEUED, DocumentVersionStatus.PROCESSING
            )
        except (InvalidLifecycleTransitionError, OptimisticConcurrencyError):
            logger.info("lost claim race", extra=extra)
            return "lost_race"
    elif version.ingestion_status is not DocumentVersionStatus.PROCESSING:
        if version.ingestion_status is DocumentVersionStatus.FAILED:
            logger.info("failed version needs explicit retry enqueue", extra=extra)
            return "skipped"
        raise PermanentIngestionError(
            f"illegal status for worker: {version.ingestion_status.value}"
        )

    claimed = replace(
        job,
        status=IngestionJobStatus.RUNNING,
        attempt_count=job.attempt_count + 1,
        correlation_id=correlation_id or job.correlation_id,
        updated_at=now,
        last_error=None,
    )
    await uow.ingestion_jobs.save(claimed)
    logger.info(
        "ingestion claimed attempt=%s",
        claimed.attempt_count,
        extra=extra,
    )

    try:
        if pipeline is not None:
            await pipeline(uow, version)  # type: ignore[operator]
        else:
            await _phase_03_stub(version.id)
    except TransientIngestionError as exc:
        await uow.ingestion_jobs.save(
            replace(
                claimed,
                last_error=str(exc),
                updated_at=utc_now(),
            )
        )
        if claimed.attempt_count >= max_attempts:
            await _fail_permanent(uow, version.id, claimed, "retry_exhausted")
            return "failed"
        return "retry"
    except PermanentIngestionError as exc:
        await _fail_permanent(uow, version.id, claimed, str(exc))
        return "failed"

    await uow.ingestion_jobs.save(
        replace(
            claimed,
            status=IngestionJobStatus.SUCCEEDED,
            last_error=None,
            updated_at=utc_now(),
        )
    )
    logger.info("phase 03 stub complete; version remains PROCESSING", extra=extra)
    return "processed"


async def _phase_03_stub(document_version_id: UUID) -> None:
    logger.info(
        "stub checkpoint document_version_id=%s",
        document_version_id,
        extra={"correlation_id": "-"},
    )


async def _fail_permanent(
    uow: UnitOfWork, version_id: UUID, job: IngestionJob, reason: str
) -> None:
    current = await uow.versions.get(version_id)
    if current is not None and current.ingestion_status is DocumentVersionStatus.PROCESSING:
        await uow.versions.transition(
            version_id,
            DocumentVersionStatus.PROCESSING,
            DocumentVersionStatus.FAILED,
            failure_code="INGESTION_FAILED",
            failure_message=reason,
        )
    await uow.ingestion_jobs.save(
        replace(
            job,
            status=IngestionJobStatus.FAILED,
            last_error=reason,
            updated_at=utc_now(),
        )
    )
