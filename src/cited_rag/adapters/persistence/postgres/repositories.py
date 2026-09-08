from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from cited_rag.adapters.persistence.postgres.errors import raise_domain_integrity_error
from cited_rag.adapters.persistence.postgres.mapping import (
    chunk_from_row,
    chunk_to_row,
    collection_from_row,
    collection_to_row,
    document_from_row,
    document_to_row,
    job_from_row,
    job_to_row,
    page_from_row,
    page_to_row,
    principal_from_row,
    principal_to_row,
    query_run_from_row,
    query_run_to_row,
    version_from_row,
    version_to_row,
)
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
from cited_rag.domain.clock import utc_now
from cited_rag.domain.enums import DocumentVersionStatus, IngestionJobStatus
from cited_rag.domain.exceptions import OptimisticConcurrencyError
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.collection import Collection
from cited_rag.domain.models.document import Document, DocumentVersion
from cited_rag.domain.models.ingestion import IngestionJob
from cited_rag.domain.models.page import Page
from cited_rag.domain.models.principal import ApiPrincipal
from cited_rag.domain.models.query import QueryRun
from cited_rag.domain.policies import assert_lifecycle_transition


class PostgresPrincipalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, principal: ApiPrincipal) -> None:
        await _add(self._session, principal_to_row(principal))

    async def get(self, principal_id: UUID) -> ApiPrincipal | None:
        row = await self._session.get(ApiPrincipalRow, principal_id)
        return principal_from_row(row) if row is not None else None


class PostgresCollectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, collection: Collection) -> None:
        await _add(self._session, collection_to_row(collection))

    async def get(self, collection_id: UUID) -> Collection | None:
        row = await self._session.get(CollectionRow, collection_id)
        return collection_from_row(row) if row is not None else None


class PostgresDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: Document) -> None:
        await _add(self._session, document_to_row(document))

    async def get(self, document_id: UUID) -> Document | None:
        row = await self._session.get(DocumentRow, document_id)
        return document_from_row(row) if row is not None else None

    async def get_for_update(self, document_id: UUID) -> Document | None:
        result = await self._session.scalars(
            select(DocumentRow).where(DocumentRow.id == document_id).with_for_update()
        )
        row = result.first()
        return document_from_row(row) if row is not None else None

    async def set_active_version(self, document_id: UUID, version_id: UUID | None) -> None:
        await self._session.execute(
            update(DocumentRow)
            .where(DocumentRow.id == document_id)
            .values(active_version_id=version_id)
        )

    async def list_searchable_version_ids(self, collection_id: UUID) -> list[UUID]:
        result = await self._session.scalars(
            select(DocumentRow.active_version_id)
            .join(DocumentVersionRow, DocumentRow.active_version_id == DocumentVersionRow.id)
            .where(
                DocumentRow.collection_id == collection_id,
                DocumentRow.deleted_at.is_(None),
                DocumentVersionRow.ingestion_status == DocumentVersionStatus.READY.value,
            )
        )
        return [version_id for version_id in result.all() if version_id is not None]

    async def mark_deleted(self, document_id: UUID) -> None:
        await self._session.execute(
            update(DocumentRow)
            .where(DocumentRow.id == document_id)
            .values(deleted_at=utc_now(), active_version_id=None)
        )


class PostgresDocumentVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, version: DocumentVersion) -> None:
        await _add(self._session, version_to_row(version))

    async def get(self, version_id: UUID) -> DocumentVersion | None:
        row = await self._session.get(DocumentVersionRow, version_id)
        return version_from_row(row) if row is not None else None

    async def list_by_document(self, document_id: UUID) -> list[DocumentVersion]:
        result = await self._session.scalars(
            select(DocumentVersionRow)
            .where(DocumentVersionRow.document_id == document_id)
            .order_by(DocumentVersionRow.version_number)
        )
        return [version_from_row(row) for row in result.all()]

    async def get_by_content_hash(
        self, collection_id: UUID, content_hash: str
    ) -> DocumentVersion | None:
        result = await self._session.scalars(
            select(DocumentVersionRow)
            .where(
                DocumentVersionRow.collection_id == collection_id,
                DocumentVersionRow.content_hash == content_hash,
                DocumentVersionRow.ingestion_status != DocumentVersionStatus.DELETED.value,
            )
            .order_by(DocumentVersionRow.created_at)
        )
        row = result.first()
        return version_from_row(row) if row is not None else None

    async def transition(
        self,
        version_id: UUID,
        from_status: DocumentVersionStatus,
        to_status: DocumentVersionStatus,
        *,
        failure_code: str | None = None,
        failure_message: str | None = None,
        page_count: int | None = None,
    ) -> DocumentVersion:
        assert_lifecycle_transition(from_status, to_status)
        values: dict[str, object] = {"ingestion_status": to_status.value}
        if to_status is DocumentVersionStatus.READY:
            values["ready_at"] = utc_now()
        if to_status is DocumentVersionStatus.FAILED:
            values["failure_code"] = failure_code
            values["failure_message"] = failure_message
        if page_count is not None:
            values["page_count"] = page_count
        result = await self._session.execute(
            update(DocumentVersionRow)
            .where(
                DocumentVersionRow.id == version_id,
                DocumentVersionRow.ingestion_status == from_status.value,
            )
            .values(**values)
        )
        if int(getattr(result, "rowcount", 0)) != 1:
            raise OptimisticConcurrencyError()
        loaded = await self.get(version_id)
        if loaded is None:
            raise OptimisticConcurrencyError()
        return loaded

    async def mark_deleting(self, version_id: UUID) -> None:
        """Park a non-READY version in DELETING before object cleanup."""
        await self._session.execute(
            update(DocumentVersionRow)
            .where(
                DocumentVersionRow.id == version_id,
                DocumentVersionRow.ingestion_status.not_in(
                    (
                        DocumentVersionStatus.READY.value,
                        DocumentVersionStatus.DELETING.value,
                        DocumentVersionStatus.DELETED.value,
                    )
                ),
            )
            .values(ingestion_status=DocumentVersionStatus.DELETING.value)
        )

    async def tombstone(self, version_id: UUID) -> None:
        """Mark a non-READY version DELETED so its content hash can be reused."""
        await self._session.execute(
            update(DocumentVersionRow)
            .where(
                DocumentVersionRow.id == version_id,
                DocumentVersionRow.ingestion_status.not_in(
                    (
                        DocumentVersionStatus.READY.value,
                        DocumentVersionStatus.DELETING.value,
                        DocumentVersionStatus.DELETED.value,
                    )
                ),
            )
            .values(ingestion_status=DocumentVersionStatus.DELETED.value)
        )

    async def set_page_count(self, version_id: UUID, page_count: int) -> None:
        await self._session.execute(
            update(DocumentVersionRow)
            .where(DocumentVersionRow.id == version_id)
            .values(page_count=page_count)
        )

    async def set_chunking_config(
        self, version_id: UUID, chunking_config: dict[str, str | int]
    ) -> None:
        await self._session.execute(
            update(DocumentVersionRow)
            .where(DocumentVersionRow.id == version_id)
            .values(chunking_config=chunking_config)
        )

    async def set_sparse_encoder_config(
        self, version_id: UUID, sparse_encoder_config: dict[str, str]
    ) -> None:
        await self._session.execute(
            update(DocumentVersionRow)
            .where(DocumentVersionRow.id == version_id)
            .values(sparse_encoder_config=sparse_encoder_config)
        )


class PostgresPageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, page: Page) -> None:
        await _add(self._session, page_to_row(page))

    async def list_by_version(self, document_version_id: UUID) -> list[Page]:
        result = await self._session.scalars(
            select(PageRow)
            .where(PageRow.document_version_id == document_version_id)
            .order_by(PageRow.page_number)
        )
        return [page_from_row(row) for row in result.all()]


class PostgresChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, chunk: Chunk) -> None:
        await _add(self._session, chunk_to_row(chunk))

    async def get(self, chunk_id: UUID) -> Chunk | None:
        row = await self._session.get(ChunkRow, chunk_id)
        return chunk_from_row(row) if row is not None else None

    async def list_by_version(self, document_version_id: UUID) -> list[Chunk]:
        result = await self._session.scalars(
            select(ChunkRow)
            .where(ChunkRow.document_version_id == document_version_id)
            .order_by(ChunkRow.chunk_order)
        )
        return [chunk_from_row(row) for row in result.all()]


class PostgresIngestionJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, job: IngestionJob) -> None:
        await _add(self._session, job_to_row(job))

    async def get_by_version(self, document_version_id: UUID) -> IngestionJob | None:
        result = await self._session.scalars(
            select(IngestionJobRow).where(
                IngestionJobRow.document_version_id == document_version_id
            )
        )
        row = result.first()
        return job_from_row(row) if row is not None else None

    async def save(self, job: IngestionJob) -> None:
        row = await self._session.get(IngestionJobRow, job.id)
        if row is None:
            await self.add(job)
            return
        row.status = job.status.value
        row.attempt_count = job.attempt_count
        row.last_error = job.last_error
        row.correlation_id = job.correlation_id
        row.updated_at = job.updated_at
        await self._session.flush()

    async def claim(self, document_version_id: UUID, *, lease_seconds: int) -> IngestionJob | None:
        now = utc_now()
        cutoff = now - timedelta(seconds=lease_seconds)
        result = await self._session.scalars(
            update(IngestionJobRow)
            .where(
                IngestionJobRow.document_version_id == document_version_id,
                or_(
                    IngestionJobRow.status == IngestionJobStatus.PENDING.value,
                    and_(
                        IngestionJobRow.status == IngestionJobStatus.RUNNING.value,
                        IngestionJobRow.updated_at <= cutoff,
                    ),
                ),
            )
            .values(
                status=IngestionJobStatus.RUNNING.value,
                attempt_count=IngestionJobRow.attempt_count + 1,
                updated_at=now,
                last_error=None,
            )
            .returning(IngestionJobRow)
        )
        row = result.first()
        return job_from_row(row) if row is not None else None


class PostgresQueryRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, query_run: QueryRun) -> None:
        await _add(self._session, query_run_to_row(query_run))

    async def get(self, query_run_id: UUID) -> QueryRun | None:
        row = await self._session.get(QueryRunRow, query_run_id)
        return query_run_from_row(row) if row is not None else None


async def _add(session: AsyncSession, row: object) -> None:
    try:
        async with session.begin_nested():
            session.add(row)
            await session.flush()
    except IntegrityError as exc:
        raise_domain_integrity_error(exc)
