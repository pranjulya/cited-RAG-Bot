from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from pydantic import BaseModel

from cited_rag.adapters.persistence.postgres.uow import PostgresUnitOfWork
from cited_rag.api.deps import get_principal, get_queue, get_settings_dep, get_storage, get_uow
from cited_rag.application.upload import (
    delete_document,
    owned_collection_or_none,
    upload_new_document,
    upload_new_version,
)
from cited_rag.config import Settings
from cited_rag.domain.exceptions import (
    EmptyUploadError,
    InvalidPdfError,
    PayloadTooLargeError,
    QueueError,
    StorageError,
)
from cited_rag.domain.models.principal import ApiPrincipal
from cited_rag.domain.policies import public_ingestion_status
from cited_rag.ports.object_storage import ObjectStorage
from cited_rag.ports.queue import JobQueue

router = APIRouter()


class UploadResponse(BaseModel):
    document_id: UUID
    document_version_id: UUID
    status: str


class DocumentStatusResponse(BaseModel):
    document_id: UUID
    collection_id: UUID
    logical_name: str
    active_version_id: UUID | None
    document_version_id: UUID | None
    version_number: int | None
    status: str | None
    original_filename: str | None


class DeleteResponse(BaseModel):
    document_id: UUID
    status: str


def _http_for_upload_error(exc: Exception) -> HTTPException:
    if isinstance(exc, EmptyUploadError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty_file")
    if isinstance(exc, InvalidPdfError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_pdf")
    if isinstance(exc, PayloadTooLargeError):
        return HTTPException(status_code=413, detail="too_large")
    if isinstance(exc, StorageError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="storage_unavailable"
        )
    if isinstance(exc, QueueError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="queue_unavailable"
        )
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="upload_failed")


@router.post(
    "/v1/collections/{collection_id}/documents",
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_document(
    collection_id: UUID,
    file: UploadFile,
    request: Request,
    principal: ApiPrincipal = Depends(get_principal),
    uow: PostgresUnitOfWork = Depends(get_uow),
    storage: ObjectStorage = Depends(get_storage),
    queue: JobQueue = Depends(get_queue),
    settings: Settings = Depends(get_settings_dep),
) -> UploadResponse:
    collection = owned_collection_or_none(await uow.collections.get(collection_id), principal.id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="collection_not_found")
    try:
        result = await upload_new_document(
            uow,
            storage,
            queue,
            collection=collection,
            upload=file,
            max_bytes=settings.max_upload_bytes,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    except (
        EmptyUploadError,
        InvalidPdfError,
        PayloadTooLargeError,
        StorageError,
        QueueError,
    ) as exc:
        raise _http_for_upload_error(exc) from exc
    return UploadResponse(
        document_id=result.document_id,
        document_version_id=result.document_version_id,
        status=result.status,
    )


@router.post(
    "/v1/collections/{collection_id}/documents/{document_id}/versions",
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_document_version(
    collection_id: UUID,
    document_id: UUID,
    file: UploadFile,
    request: Request,
    principal: ApiPrincipal = Depends(get_principal),
    uow: PostgresUnitOfWork = Depends(get_uow),
    storage: ObjectStorage = Depends(get_storage),
    queue: JobQueue = Depends(get_queue),
    settings: Settings = Depends(get_settings_dep),
) -> UploadResponse:
    collection = owned_collection_or_none(await uow.collections.get(collection_id), principal.id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="collection_not_found")
    document = await uow.documents.get(document_id)
    if (
        document is None
        or document.collection_id != collection.id
        or document.deleted_at is not None
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document_not_found")
    try:
        result = await upload_new_version(
            uow,
            storage,
            queue,
            collection=collection,
            document=document,
            upload=file,
            max_bytes=settings.max_upload_bytes,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    except (
        EmptyUploadError,
        InvalidPdfError,
        PayloadTooLargeError,
        StorageError,
        QueueError,
    ) as exc:
        raise _http_for_upload_error(exc) from exc
    return UploadResponse(
        document_id=result.document_id,
        document_version_id=result.document_version_id,
        status=result.status,
    )


@router.get("/v1/documents/{document_id}")
async def get_document(
    document_id: UUID,
    principal: ApiPrincipal = Depends(get_principal),
    uow: PostgresUnitOfWork = Depends(get_uow),
) -> DocumentStatusResponse:
    document = await uow.documents.get(document_id)
    if document is None or document.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document_not_found")
    collection = owned_collection_or_none(
        await uow.collections.get(document.collection_id), principal.id
    )
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document_not_found")
    versions = await uow.versions.list_by_document(document.id)
    current = versions[-1] if versions else None
    return DocumentStatusResponse(
        document_id=document.id,
        collection_id=document.collection_id,
        logical_name=document.logical_name,
        active_version_id=document.active_version_id,
        document_version_id=current.id if current else None,
        version_number=current.version_number if current else None,
        status=public_ingestion_status(current.ingestion_status) if current else None,
        original_filename=current.original_filename if current else None,
    )


@router.delete("/v1/documents/{document_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_document_route(
    document_id: UUID,
    request: Request,
    principal: ApiPrincipal = Depends(get_principal),
    uow: PostgresUnitOfWork = Depends(get_uow),
    queue: JobQueue = Depends(get_queue),
) -> DeleteResponse:
    document = await uow.documents.get(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document_not_found")
    collection = owned_collection_or_none(
        await uow.collections.get(document.collection_id), principal.id
    )
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document_not_found")
    try:
        await delete_document(
            uow,
            queue,
            document=document,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    except QueueError as exc:
        raise _http_for_upload_error(exc) from exc
    return DeleteResponse(document_id=document.id, status="DELETING")
