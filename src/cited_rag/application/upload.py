from __future__ import annotations

import hashlib
import tempfile
from collections.abc import AsyncIterator
from dataclasses import dataclass, replace
from pathlib import Path
from uuid import UUID, uuid5

from fastapi import UploadFile

from cited_rag.domain.enums import DocumentVersionStatus, IngestionJobStatus
from cited_rag.domain.exceptions import (
    DuplicateIdentityError,
    EmptyUploadError,
    PayloadTooLargeError,
    QueueError,
)
from cited_rag.domain.models.collection import Collection
from cited_rag.domain.models.document import Document, DocumentVersion
from cited_rag.domain.models.ingestion import IngestionJob
from cited_rag.domain.models.principal import ApiPrincipal
from cited_rag.domain.pdf import validate_pdf_envelope
from cited_rag.domain.policies import public_ingestion_status
from cited_rag.ports.object_storage import ObjectStorage, source_pdf_key
from cited_rag.ports.queue import JobQueue
from cited_rag.ports.repositories import UnitOfWork

DEFAULT_PRINCIPAL_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
DEFAULT_PRINCIPAL_NAME = "v1-api-key-principal"


def default_principal_id() -> UUID:
    return uuid5(DEFAULT_PRINCIPAL_NAMESPACE, DEFAULT_PRINCIPAL_NAME)


@dataclass(frozen=True, slots=True)
class UploadResult:
    document_id: UUID
    document_version_id: UUID
    status: str
    idempotent: bool


async def ensure_principal(uow: UnitOfWork) -> ApiPrincipal:
    principal_id = default_principal_id()
    existing = await uow.principals.get(principal_id)
    if existing is not None:
        return existing
    principal = ApiPrincipal(id=principal_id, name=DEFAULT_PRINCIPAL_NAME)
    try:
        await uow.principals.add(principal)
    except DuplicateIdentityError:
        loaded = await uow.principals.get(principal_id)
        if loaded is None:
            raise
        return loaded
    return principal


async def create_collection(uow: UnitOfWork, *, name: str, owner_id: UUID) -> Collection:
    collection = Collection(name=name.strip(), owner_id=owner_id)
    await uow.collections.add(collection)
    await uow.commit()
    return collection


def owned_collection_or_none(collection: Collection | None, owner_id: UUID) -> Collection | None:
    if collection is None or collection.owner_id != owner_id:
        return None
    return collection


async def upload_new_document(
    uow: UnitOfWork,
    storage: ObjectStorage,
    queue: JobQueue,
    *,
    collection: Collection,
    upload: UploadFile,
    max_bytes: int,
    correlation_id: str | None = None,
) -> UploadResult:
    spool = await _spool_pdf(upload, max_bytes)
    try:
        duplicate = await _existing_hash(
            uow, queue, collection.id, spool.content_hash, correlation_id
        )
        if duplicate is not None:
            return duplicate
        document = Document(collection_id=collection.id, logical_name=spool.filename)
        version = DocumentVersion(
            document_id=document.id,
            collection_id=collection.id,
            version_number=1,
            content_hash=spool.content_hash,
            original_filename=spool.filename,
            mime_type="application/pdf",
            size_bytes=spool.size_bytes,
            storage_uri="",
        )
        return await _persist_new_version(
            uow,
            storage,
            queue,
            collection=collection,
            document=document,
            version=version,
            spool=spool,
            correlation_id=correlation_id,
        )
    finally:
        spool.path.unlink(missing_ok=True)


async def upload_new_version(
    uow: UnitOfWork,
    storage: ObjectStorage,
    queue: JobQueue,
    *,
    collection: Collection,
    document: Document,
    upload: UploadFile,
    max_bytes: int,
    correlation_id: str | None = None,
) -> UploadResult:
    spool = await _spool_pdf(upload, max_bytes)
    try:
        duplicate = await _existing_hash(
            uow, queue, collection.id, spool.content_hash, correlation_id
        )
        if duplicate is not None:
            return duplicate
        await uow.documents.get_for_update(document.id)
        versions = await uow.versions.list_by_document(document.id)
        next_number = max((item.version_number for item in versions), default=0) + 1
        version = DocumentVersion(
            document_id=document.id,
            collection_id=collection.id,
            version_number=next_number,
            content_hash=spool.content_hash,
            original_filename=spool.filename,
            mime_type="application/pdf",
            size_bytes=spool.size_bytes,
            storage_uri="",
        )
        return await _persist_new_version(
            uow,
            storage,
            queue,
            collection=collection,
            document=None,
            version=version,
            spool=spool,
            correlation_id=correlation_id,
        )
    finally:
        spool.path.unlink(missing_ok=True)


async def delete_document(
    uow: UnitOfWork,
    queue: JobQueue,
    *,
    document: Document,
    correlation_id: str | None = None,
) -> None:
    from cited_rag.application.deletion import tombstone_document

    await tombstone_document(uow, queue, document_id=document.id, correlation_id=correlation_id)


async def _existing_hash(
    uow: UnitOfWork,
    queue: JobQueue,
    collection_id: UUID,
    content_hash: str,
    correlation_id: str | None,
) -> UploadResult | None:
    existing = await uow.versions.get_by_content_hash(collection_id, content_hash)
    if existing is None:
        return None
    if existing.ingestion_status is DocumentVersionStatus.FAILED:
        await uow.versions.transition(
            existing.id, DocumentVersionStatus.FAILED, DocumentVersionStatus.QUEUED
        )
        job = await _ensure_pending_job(uow, existing.id, correlation_id)
        await uow.commit()
        await queue.enqueue_ingestion(existing.id, correlation_id, attempt=job.attempt_count)
        return UploadResult(
            document_id=existing.document_id,
            document_version_id=existing.id,
            status=DocumentVersionStatus.QUEUED.value,
            idempotent=True,
        )
    if existing.ingestion_status is DocumentVersionStatus.UPLOADED:
        await _ensure_pending_job(uow, existing.id, correlation_id)
        await uow.versions.transition(
            existing.id, DocumentVersionStatus.UPLOADED, DocumentVersionStatus.QUEUED
        )
        await uow.commit()
        await queue.enqueue_ingestion(existing.id, correlation_id, attempt=None)
        return UploadResult(
            document_id=existing.document_id,
            document_version_id=existing.id,
            status=DocumentVersionStatus.QUEUED.value,
            idempotent=True,
        )
    return UploadResult(
        document_id=existing.document_id,
        document_version_id=existing.id,
        status=public_ingestion_status(existing.ingestion_status),
        idempotent=True,
    )


async def _persist_new_version(
    uow: UnitOfWork,
    storage: ObjectStorage,
    queue: JobQueue,
    *,
    collection: Collection,
    document: Document | None,
    version: DocumentVersion,
    spool: _Spool,
    correlation_id: str | None,
) -> UploadResult:
    key = source_pdf_key(
        collection_id=collection.id,
        document_id=version.document_id,
        version_id=version.id,
    )
    owned = False
    try:
        uri = await storage.put(key, _file_chunks(spool.path))
        stored = replace(version, storage_uri=uri, ingestion_status=DocumentVersionStatus.QUEUED)
        if document is not None:
            await uow.documents.add(document)
        await uow.versions.add(stored)
        await uow.ingestion_jobs.add(
            IngestionJob(document_version_id=stored.id, correlation_id=correlation_id)
        )
        await uow.commit()
        owned = True
        await queue.enqueue_ingestion(stored.id, correlation_id, attempt=None)
    except QueueError:
        raise
    except Exception:
        if not owned:
            await storage.delete(key)
        duplicate = await _existing_hash(
            uow, queue, collection.id, spool.content_hash, correlation_id
        )
        if duplicate is not None:
            return duplicate
        raise
    return UploadResult(
        document_id=stored.document_id,
        document_version_id=stored.id,
        status=DocumentVersionStatus.QUEUED.value,
        idempotent=False,
    )


async def _ensure_pending_job(
    uow: UnitOfWork, version_id: UUID, correlation_id: str | None
) -> IngestionJob:
    existing = await uow.ingestion_jobs.get_by_version(version_id)
    if existing is None:
        job = IngestionJob(document_version_id=version_id, correlation_id=correlation_id)
        await uow.ingestion_jobs.add(job)
        return job
    reset = replace(
        existing,
        status=IngestionJobStatus.PENDING,
        last_error=None,
        correlation_id=correlation_id or existing.correlation_id,
    )
    await uow.ingestion_jobs.save(reset)
    return reset


@dataclass(frozen=True, slots=True)
class _Spool:
    path: Path
    content_hash: str
    size_bytes: int
    filename: str


async def _spool_pdf(upload: UploadFile, max_bytes: int) -> _Spool:
    filename = upload.filename or ""
    first = await upload.read(64 * 1024)
    if not first:
        raise EmptyUploadError()
    if len(first) > max_bytes:
        raise PayloadTooLargeError()
    validate_pdf_envelope(
        filename=filename,
        content_type=upload.content_type,
        size_bytes=len(first),
        head=first[:8],
        max_bytes=max_bytes,
    )
    hasher = hashlib.sha256()
    hasher.update(first)
    size = len(first)
    handle = tempfile.NamedTemporaryFile(prefix="cited-rag-upload-", suffix=".pdf", delete=False)
    dest = Path(handle.name)
    try:
        handle.write(first)
        while True:
            chunk = await upload.read(64 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                raise PayloadTooLargeError()
            hasher.update(chunk)
            handle.write(chunk)
    except Exception:
        handle.close()
        dest.unlink(missing_ok=True)
        raise
    handle.close()
    return _Spool(
        path=dest,
        content_hash=hasher.hexdigest(),
        size_bytes=size,
        filename=filename,
    )


async def _file_chunks(path: Path, chunk_size: int = 64 * 1024) -> AsyncIterator[bytes]:
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            yield chunk
