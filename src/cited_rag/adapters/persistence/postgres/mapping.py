from __future__ import annotations

from cited_rag.adapters.persistence.postgres.models import (
    ApiPrincipalRow,
    ChunkRow,
    CollectionRow,
    DocumentRow,
    DocumentVersionRow,
    IngestionJobRow,
    PageRow,
    QueryRunRow,
)
from cited_rag.domain.enums import (
    CollectionStatus,
    DocumentVersionStatus,
    IngestionJobStatus,
    QueryRunStatus,
)
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.collection import Collection
from cited_rag.domain.models.document import Document, DocumentVersion
from cited_rag.domain.models.ingestion import IngestionJob
from cited_rag.domain.models.page import Page
from cited_rag.domain.models.principal import ApiPrincipal
from cited_rag.domain.models.query import QueryRun


def principal_to_row(principal: ApiPrincipal) -> ApiPrincipalRow:
    return ApiPrincipalRow(id=principal.id, name=principal.name, created_at=principal.created_at)


def principal_from_row(row: ApiPrincipalRow) -> ApiPrincipal:
    return ApiPrincipal(id=row.id, name=row.name, created_at=row.created_at)


def collection_to_row(collection: Collection) -> CollectionRow:
    return CollectionRow(
        id=collection.id,
        name=collection.name,
        owner_id=collection.owner_id,
        status=collection.status.value,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


def collection_from_row(row: CollectionRow) -> Collection:
    return Collection(
        id=row.id,
        name=row.name,
        owner_id=row.owner_id,
        status=CollectionStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def document_to_row(document: Document) -> DocumentRow:
    return DocumentRow(
        id=document.id,
        collection_id=document.collection_id,
        logical_name=document.logical_name,
        active_version_id=document.active_version_id,
        created_at=document.created_at,
        deleted_at=document.deleted_at,
    )


def document_from_row(row: DocumentRow) -> Document:
    return Document(
        id=row.id,
        collection_id=row.collection_id,
        logical_name=row.logical_name,
        active_version_id=row.active_version_id,
        created_at=row.created_at,
        deleted_at=row.deleted_at,
    )


def version_to_row(version: DocumentVersion) -> DocumentVersionRow:
    return DocumentVersionRow(
        id=version.id,
        document_id=version.document_id,
        collection_id=version.collection_id,
        version_number=version.version_number,
        content_hash=version.content_hash,
        original_filename=version.original_filename,
        mime_type=version.mime_type,
        size_bytes=version.size_bytes,
        storage_uri=version.storage_uri,
        ingestion_status=version.ingestion_status.value,
        failure_code=version.failure_code,
        failure_message=version.failure_message,
        page_count=version.page_count,
        chunking_config=version.chunking_config,
        sparse_encoder_config=version.sparse_encoder_config,
        created_at=version.created_at,
        ready_at=version.ready_at,
    )


def version_from_row(row: DocumentVersionRow) -> DocumentVersion:
    return DocumentVersion(
        id=row.id,
        document_id=row.document_id,
        collection_id=row.collection_id,
        version_number=row.version_number,
        content_hash=row.content_hash,
        original_filename=row.original_filename,
        mime_type=row.mime_type,
        size_bytes=row.size_bytes,
        storage_uri=row.storage_uri,
        ingestion_status=DocumentVersionStatus(row.ingestion_status),
        failure_code=row.failure_code,
        failure_message=row.failure_message,
        page_count=row.page_count,
        chunking_config=row.chunking_config,
        sparse_encoder_config=row.sparse_encoder_config,
        created_at=row.created_at,
        ready_at=row.ready_at,
    )


def page_to_row(page: Page) -> PageRow:
    return PageRow(
        id=page.id,
        document_version_id=page.document_version_id,
        page_number=page.page_number,
        raw_text=page.raw_text,
        normalized_text=page.normalized_text,
        extraction_metadata=page.extraction_metadata,
    )


def page_from_row(row: PageRow) -> Page:
    return Page(
        id=row.id,
        document_version_id=row.document_version_id,
        page_number=row.page_number,
        raw_text=row.raw_text,
        normalized_text=row.normalized_text,
        extraction_metadata=row.extraction_metadata,
    )


def chunk_to_row(chunk: Chunk) -> ChunkRow:
    return ChunkRow(
        id=chunk.id,
        collection_id=chunk.collection_id,
        document_id=chunk.document_id,
        document_version_id=chunk.document_version_id,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        chunk_order=chunk.chunk_order,
        text=chunk.text,
        token_count=chunk.token_count,
        content_hash=chunk.content_hash,
        created_at=chunk.created_at,
    )


def chunk_from_row(row: ChunkRow) -> Chunk:
    return Chunk(
        collection_id=row.collection_id,
        document_id=row.document_id,
        document_version_id=row.document_version_id,
        page_start=row.page_start,
        page_end=row.page_end,
        chunk_order=row.chunk_order,
        text=row.text,
        content_hash=row.content_hash,
        token_count=row.token_count,
        created_at=row.created_at,
    )


def job_to_row(job: IngestionJob) -> IngestionJobRow:
    return IngestionJobRow(
        id=job.id,
        document_version_id=job.document_version_id,
        status=job.status.value,
        attempt_count=job.attempt_count,
        last_error=job.last_error,
        correlation_id=job.correlation_id,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def job_from_row(row: IngestionJobRow) -> IngestionJob:
    return IngestionJob(
        id=row.id,
        document_version_id=row.document_version_id,
        status=IngestionJobStatus(row.status),
        attempt_count=row.attempt_count,
        last_error=row.last_error,
        correlation_id=row.correlation_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def query_run_to_row(query_run: QueryRun) -> QueryRunRow:
    return QueryRunRow(
        id=query_run.id,
        collection_id=query_run.collection_id,
        principal_id=query_run.principal_id,
        question=query_run.question,
        status=query_run.status.value,
        correlation_id=query_run.correlation_id,
        created_at=query_run.created_at,
    )


def query_run_from_row(row: QueryRunRow) -> QueryRun:
    return QueryRun(
        id=row.id,
        collection_id=row.collection_id,
        principal_id=row.principal_id,
        question=row.question,
        status=QueryRunStatus(row.status),
        correlation_id=row.correlation_id,
        created_at=row.created_at,
    )
