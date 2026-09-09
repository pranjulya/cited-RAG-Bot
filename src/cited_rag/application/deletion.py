from __future__ import annotations

import logging
from uuid import UUID

from cited_rag.domain.enums import DocumentVersionStatus
from cited_rag.domain.exceptions import TransientIngestionError
from cited_rag.ports.object_storage import ObjectStorage, source_pdf_key
from cited_rag.ports.queue import JobQueue
from cited_rag.ports.repositories import UnitOfWork
from cited_rag.ports.retrieval_store import RetrievalStore

logger = logging.getLogger("cited_rag.deletion")


async def tombstone_document(
    uow: UnitOfWork,
    queue: JobQueue,
    *,
    document_id: UUID,
    correlation_id: str | None = None,
) -> None:
    """Make the document unsearchable, then enqueue retryable index/storage purge."""
    document = await uow.documents.get(document_id)
    if document is None:
        return
    if document.deleted_at is not None:
        await queue.enqueue_cleanup(document.id, correlation_id)
        logger.info(
            "cleanup re-enqueued id=%s",
            document.id,
            extra={"correlation_id": correlation_id or "-"},
        )
        return
    versions = await uow.versions.list_by_document(document.id)
    for version in versions:
        if version.ingestion_status is DocumentVersionStatus.DELETED:
            continue
        if version.ingestion_status is DocumentVersionStatus.READY:
            await uow.versions.transition(
                version.id, DocumentVersionStatus.READY, DocumentVersionStatus.DELETING
            )
        elif version.ingestion_status is not DocumentVersionStatus.DELETING:
            await uow.versions.mark_deleting(version.id)
    await uow.documents.mark_deleted(document.id)
    await uow.commit()
    await queue.enqueue_cleanup(document.id, correlation_id)
    logger.info(
        "document tombstoned id=%s",
        document.id,
        extra={"correlation_id": correlation_id or "-"},
    )


async def purge_deleted_document(
    uow: UnitOfWork,
    storage: ObjectStorage,
    store: RetrievalStore,
    *,
    document_id: UUID,
) -> None:
    """Idempotent cleanup: drop Qdrant points, source PDF, then DELETED."""
    versions = await uow.versions.list_by_document(document_id)
    for version in versions:
        if version.ingestion_status is DocumentVersionStatus.DELETED:
            continue
        try:
            await store.delete_version_points(version.id)
        except TransientIngestionError:
            raise
        key = source_pdf_key(
            collection_id=version.collection_id,
            document_id=version.document_id,
            version_id=version.id,
        )
        await storage.delete(key)
        current = await uow.versions.get(version.id)
        if current is not None and current.ingestion_status is DocumentVersionStatus.DELETING:
            await uow.versions.transition(
                version.id, DocumentVersionStatus.DELETING, DocumentVersionStatus.DELETED
            )
    await uow.commit()
    logger.info("document purged id=%s", document_id, extra={"correlation_id": "-"})
