from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cited_rag.adapters.persistence.postgres.errors import raise_domain_integrity_error
from cited_rag.adapters.persistence.postgres.repositories import (
    PostgresChunkRepository,
    PostgresCollectionRepository,
    PostgresDocumentRepository,
    PostgresDocumentVersionRepository,
    PostgresIngestionJobRepository,
    PostgresPageRepository,
    PostgresPrincipalRepository,
    PostgresQueryRunRepository,
)
from cited_rag.ports.repositories import (
    ChunkRepository,
    CollectionRepository,
    DocumentRepository,
    DocumentVersionRepository,
    IngestionJobRepository,
    PageRepository,
    PrincipalRepository,
    QueryRunRepository,
)


class PostgresUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None
        self.principals: PrincipalRepository
        self.collections: CollectionRepository
        self.documents: DocumentRepository
        self.versions: DocumentVersionRepository
        self.pages: PageRepository
        self.chunks: ChunkRepository
        self.ingestion_jobs: IngestionJobRepository
        self.query_runs: QueryRunRepository

    async def __aenter__(self) -> PostgresUnitOfWork:
        self.session = self._session_factory()
        self.principals = PostgresPrincipalRepository(self.session)
        self.collections = PostgresCollectionRepository(self.session)
        self.documents = PostgresDocumentRepository(self.session)
        self.versions = PostgresDocumentVersionRepository(self.session)
        self.pages = PostgresPageRepository(self.session)
        self.chunks = PostgresChunkRepository(self.session)
        self.ingestion_jobs = PostgresIngestionJobRepository(self.session)
        self.query_runs = PostgresQueryRunRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        if self.session is None:
            return
        try:
            if exc_type is not None:
                await self.session.rollback()
        finally:
            await self.session.close()
            self.session = None

    async def commit(self) -> None:
        if self.session is None:
            return
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise_domain_integrity_error(exc)

    async def rollback(self) -> None:
        if self.session is None:
            return
        await self.session.rollback()
