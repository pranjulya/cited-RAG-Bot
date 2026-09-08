from __future__ import annotations

import logging
from dataclasses import replace
from uuid import UUID

from cited_rag.application.chunking import persist_chunks
from cited_rag.application.indexing import finalize_ready, persist_dense_index, persist_sparse_index
from cited_rag.application.parsing import persist_parsed_pages
from cited_rag.domain.clock import utc_now
from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.enums import DocumentVersionStatus, IngestionJobStatus
from cited_rag.domain.exceptions import (
    InvalidLifecycleTransitionError,
    OptimisticConcurrencyError,
    PermanentIngestionError,
    TransientIngestionError,
)
from cited_rag.domain.models.ingestion import IngestionJob
from cited_rag.ports.chunker import Chunker
from cited_rag.ports.embedding import EmbeddingProvider
from cited_rag.ports.object_storage import ObjectStorage
from cited_rag.ports.parser import DocumentParser
from cited_rag.ports.repositories import UnitOfWork
from cited_rag.ports.retrieval_store import RetrievalStore
from cited_rag.ports.sparse_encoder import SparseEncoder

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
    storage: ObjectStorage | None = None,
    parser: DocumentParser | None = None,
    chunker: Chunker | None = None,
    embedding_provider: EmbeddingProvider | None = None,
    retrieval_store: RetrievalStore | None = None,
    embedding_config: EmbeddingConfig | None = None,
    sparse_encoder: SparseEncoder | None = None,
) -> str:
    """Claim a version, parse, chunk, dense+sparse index, READY if complete."""
    extra = {"correlation_id": correlation_id or "-"}
    version = await uow.versions.get(document_version_id)
    if version is None:
        raise PermanentIngestionError("document version not found")

    if version.ingestion_status is DocumentVersionStatus.READY:
        logger.info("already processed; skip duplicate delivery", extra=extra)
        return "duplicate"
    if version.ingestion_status in {
        DocumentVersionStatus.DELETING,
        DocumentVersionStatus.DELETED,
    }:
        logger.info("skip ingestion for terminal version", extra=extra)
        return "skipped"

    if version.ingestion_status is DocumentVersionStatus.FAILED:
        logger.info("failed version needs explicit retry enqueue", extra=extra)
        return "skipped"

    existing = await uow.ingestion_jobs.get_by_version(document_version_id)
    if existing is None:
        await uow.ingestion_jobs.add(
            IngestionJob(document_version_id=document_version_id, correlation_id=correlation_id)
        )

    if (
        existing is not None
        and existing.status is IngestionJobStatus.SUCCEEDED
        and version.ingestion_status is DocumentVersionStatus.PROCESSING
    ):
        logger.info("already processed; skip duplicate delivery", extra=extra)
        return "duplicate"

    claimed = await uow.ingestion_jobs.claim(document_version_id, lease_seconds=lease_seconds)
    if claimed is None:
        logger.info("lease held or not claimable; skip duplicate delivery", extra=extra)
        return "leased"

    if claimed.attempt_count > max_attempts:
        await _fail_permanent(uow, version.id, claimed, "retry_exhausted")
        await uow.commit()
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
            await uow.ingestion_jobs.save(
                replace(claimed, status=IngestionJobStatus.PENDING, updated_at=utc_now())
            )
            await uow.commit()
            logger.info("lost claim race", extra=extra)
            return "lost_race"
    elif version.ingestion_status is not DocumentVersionStatus.PROCESSING:
        raise PermanentIngestionError(
            f"illegal status for worker: {version.ingestion_status.value}"
        )

    logger.info("ingestion claimed attempt=%s", claimed.attempt_count, extra=extra)

    try:
        if pipeline is not None:
            await pipeline(uow, version)  # type: ignore[operator]
        elif storage is not None and parser is not None:
            if chunker is None:
                raise PermanentIngestionError("ingestion chunker is not configured")
            if embedding_provider is None or retrieval_store is None or embedding_config is None:
                raise PermanentIngestionError("ingestion dense indexer is not configured")
            if sparse_encoder is None:
                raise PermanentIngestionError("ingestion sparse encoder is not configured")
            pages = await persist_parsed_pages(uow, version, storage=storage, parser=parser)
            chunks = await persist_chunks(uow, version, pages, chunker)
            await persist_dense_index(
                chunks,
                embedder=embedding_provider,
                store=retrieval_store,
                config=embedding_config,
            )
            await persist_sparse_index(
                chunks,
                encoder=sparse_encoder,
                store=retrieval_store,
                config=embedding_config,
            )
            await finalize_ready(
                uow,
                version,
                chunks,
                store=retrieval_store,
                encoder_config=sparse_encoder.config,
                index_version=embedding_config.index_version,
            )
        else:
            raise PermanentIngestionError("ingestion parser is not configured")
    except TransientIngestionError as exc:
        await uow.ingestion_jobs.save(
            replace(
                claimed,
                status=IngestionJobStatus.PENDING,
                last_error=str(exc),
                updated_at=utc_now(),
            )
        )
        if claimed.attempt_count >= max_attempts:
            await _fail_permanent(uow, version.id, claimed, "retry_exhausted")
            await uow.commit()
            return "failed"
        await uow.commit()
        return "retry"
    except PermanentIngestionError as exc:
        await _fail_permanent(
            uow,
            version.id,
            claimed,
            str(exc),
            failure_code=exc.failure_code,
        )
        await uow.commit()
        return "failed"

    await uow.ingestion_jobs.save(
        replace(
            claimed,
            status=IngestionJobStatus.SUCCEEDED,
            last_error=None,
            updated_at=utc_now(),
        )
    )
    await uow.commit()
    logger.info("ingestion complete; version READY after dense+sparse", extra=extra)
    return "processed"


async def _fail_permanent(
    uow: UnitOfWork,
    version_id: UUID,
    job: IngestionJob,
    reason: str,
    *,
    failure_code: str = "INGESTION_FAILED",
) -> None:
    current = await uow.versions.get(version_id)
    if current is not None and current.ingestion_status is DocumentVersionStatus.PROCESSING:
        await uow.versions.transition(
            version_id,
            DocumentVersionStatus.PROCESSING,
            DocumentVersionStatus.FAILED,
            failure_code=failure_code,
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
