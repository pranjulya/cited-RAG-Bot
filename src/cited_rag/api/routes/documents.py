from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, status
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
from cited_rag.domain.enums import DocumentVersionStatus
from cited_rag.domain.exceptions import (
    EmptyUploadError,
    InvalidPdfError,
    PayloadTooLargeError,
    QueueError,
    StorageError,
)
from cited_rag.domain.models.document import Document, DocumentVersion
from cited_rag.domain.models.principal import ApiPrincipal
from cited_rag.domain.policies import public_ingestion_status
from cited_rag.ports.object_storage import ObjectStorage, source_pdf_key
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
    failure_code: str | None = None
    failure_message: str | None = None


class DeleteResponse(BaseModel):
    document_id: UUID
    status: str


def _document_status_response(
    document: Document, current: DocumentVersion | None
) -> DocumentStatusResponse:
    if current is None:
        return DocumentStatusResponse(
            document_id=document.id,
            collection_id=document.collection_id,
            logical_name=document.logical_name,
            active_version_id=document.active_version_id,
            document_version_id=None,
            version_number=None,
            status=None,
            original_filename=None,
            failure_code=None,
            failure_message=None,
        )
    failed = current.ingestion_status is DocumentVersionStatus.FAILED
    return DocumentStatusResponse(
        document_id=document.id,
        collection_id=document.collection_id,
        logical_name=document.logical_name,
        active_version_id=document.active_version_id,
        document_version_id=current.id,
        version_number=current.version_number,
        status=public_ingestion_status(current.ingestion_status),
        original_filename=current.original_filename,
        failure_code=current.failure_code if failed else None,
        failure_message=current.failure_message if failed else None,
    )


def _source_version(document: Document, versions: list[DocumentVersion]) -> DocumentVersion | None:
    if document.active_version_id is not None:
        for version in versions:
            if version.id == document.active_version_id and version.storage_uri:
                return version
    return next((version for version in reversed(versions) if version.storage_uri), None)


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


@router.get("/v1/collections/{collection_id}/documents")
async def list_documents(
    collection_id: UUID,
    principal: ApiPrincipal = Depends(get_principal),
    uow: PostgresUnitOfWork = Depends(get_uow),
) -> list[DocumentStatusResponse]:
    collection = owned_collection_or_none(await uow.collections.get(collection_id), principal.id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="collection_not_found")
    documents = await uow.documents.list_by_collection(collection.id)
    responses = []
    for document in documents:
        versions = await uow.versions.list_by_document(document.id)
        responses.append(_document_status_response(document, versions[-1] if versions else None))
    return responses


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
    return _document_status_response(document, current)


@router.get("/v1/documents/{document_id}/content")
async def get_document_content(
    document_id: UUID,
    principal: ApiPrincipal = Depends(get_principal),
    uow: PostgresUnitOfWork = Depends(get_uow),
    storage: ObjectStorage = Depends(get_storage),
    settings: Settings = Depends(get_settings_dep),
) -> Response:
    document = await uow.documents.get(document_id)
    if document is None or document.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document_not_found")
    collection = owned_collection_or_none(
        await uow.collections.get(document.collection_id), principal.id
    )
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document_not_found")
    version = _source_version(document, await uow.versions.list_by_document(document.id))
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document_not_found")
    key = source_pdf_key(
        collection_id=version.collection_id,
        document_id=version.document_id,
        version_id=version.id,
    )
    try:
        content = await storage.get(key)
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="storage_unavailable",
        ) from exc
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="too_large")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Cache-Control": "private, no-store"},
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
