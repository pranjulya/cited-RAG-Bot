from __future__ import annotations

from typing import Protocol
from uuid import UUID

from cited_rag.domain.enums import DocumentVersionStatus
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.collection import Collection
from cited_rag.domain.models.document import Document, DocumentVersion
from cited_rag.domain.models.ingestion import IngestionJob
from cited_rag.domain.models.page import Page
from cited_rag.domain.models.principal import ApiPrincipal
from cited_rag.domain.models.query import QueryRun


class PrincipalRepository(Protocol):
    async def add(self, principal: ApiPrincipal) -> None: ...

    async def get(self, principal_id: UUID) -> ApiPrincipal | None: ...


class CollectionRepository(Protocol):
    async def add(self, collection: Collection) -> None: ...

    async def get(self, collection_id: UUID) -> Collection | None: ...


class DocumentRepository(Protocol):
    async def add(self, document: Document) -> None: ...

    async def get(self, document_id: UUID) -> Document | None: ...

    async def get_for_update(self, document_id: UUID) -> Document | None: ...

    async def set_active_version(self, document_id: UUID, version_id: UUID | None) -> None: ...

    async def mark_deleted(self, document_id: UUID) -> None: ...


class DocumentVersionRepository(Protocol):
    async def add(self, version: DocumentVersion) -> None: ...

    async def get(self, version_id: UUID) -> DocumentVersion | None: ...

    async def list_by_document(self, document_id: UUID) -> list[DocumentVersion]: ...

    async def get_by_content_hash(
        self, collection_id: UUID, content_hash: str
    ) -> DocumentVersion | None: ...

    async def transition(
        self,
        version_id: UUID,
        from_status: DocumentVersionStatus,
        to_status: DocumentVersionStatus,
        *,
        failure_code: str | None = None,
        failure_message: str | None = None,
        page_count: int | None = None,
    ) -> DocumentVersion: ...

    async def mark_deleting(self, version_id: UUID) -> None: ...

    async def tombstone(self, version_id: UUID) -> None: ...

    async def set_page_count(self, version_id: UUID, page_count: int) -> None: ...

    async def set_chunking_config(
        self, version_id: UUID, chunking_config: dict[str, str | int]
    ) -> None: ...


class PageRepository(Protocol):
    async def add(self, page: Page) -> None: ...

    async def list_by_version(self, document_version_id: UUID) -> list[Page]: ...


class ChunkRepository(Protocol):
    async def add(self, chunk: Chunk) -> None: ...

    async def get(self, chunk_id: UUID) -> Chunk | None: ...

    async def list_by_version(self, document_version_id: UUID) -> list[Chunk]: ...


class IngestionJobRepository(Protocol):
    async def add(self, job: IngestionJob) -> None: ...

    async def get_by_version(self, document_version_id: UUID) -> IngestionJob | None: ...

    async def save(self, job: IngestionJob) -> None: ...

    async def claim(
        self, document_version_id: UUID, *, lease_seconds: int
    ) -> IngestionJob | None: ...


class QueryRunRepository(Protocol):
    async def add(self, query_run: QueryRun) -> None: ...

    async def get(self, query_run_id: UUID) -> QueryRun | None: ...


class UnitOfWork(Protocol):
    principals: PrincipalRepository
    collections: CollectionRepository
    documents: DocumentRepository
    versions: DocumentVersionRepository
    pages: PageRepository
    chunks: ChunkRepository
    ingestion_jobs: IngestionJobRepository
    query_runs: QueryRunRepository

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
