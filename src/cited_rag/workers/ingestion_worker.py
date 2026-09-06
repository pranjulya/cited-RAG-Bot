from __future__ import annotations

import os
from uuid import UUID

from arq import Retry
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from cited_rag.adapters.persistence.postgres.session import create_engine, create_session_factory
from cited_rag.adapters.persistence.postgres.uow import PostgresUnitOfWork
from cited_rag.application.ingestion import process_ingestion_job
from cited_rag.config import get_settings


async def ingest_document_version(
    ctx: dict[str, object],
    document_version_id: str,
    correlation_id: str | None = None,
) -> str:
    factory = ctx["session_factory"]
    assert isinstance(factory, async_sessionmaker)
    settings = get_settings()
    async with PostgresUnitOfWork(factory) as uow:
        outcome = await process_ingestion_job(
            uow,
            document_version_id=UUID(document_version_id),
            correlation_id=correlation_id,
            max_attempts=settings.ingestion_max_attempts,
            lease_seconds=settings.ingestion_lease_seconds,
        )
    if outcome == "retry":
        raise Retry(defer=settings.ingestion_lease_seconds + 1)
    return outcome


async def startup(ctx: dict[str, object]) -> None:
    settings = get_settings()
    if settings.database_url is None:
        raise RuntimeError("CITED_RAG_DATABASE_URL is required for the ingestion worker")
    engine = create_engine(settings.database_url.get_secret_value())
    ctx["engine"] = engine
    ctx["session_factory"] = create_session_factory(engine)


async def shutdown(ctx: dict[str, object]) -> None:
    engine = ctx.get("engine")
    if isinstance(engine, AsyncEngine):
        await engine.dispose()


class WorkerSettings:
    functions = [ingest_document_version]
    on_startup = startup
    on_shutdown = shutdown
    max_tries = 10
    job_timeout = 60
    redis_settings = RedisSettings.from_dsn(
        os.environ.get("CITED_RAG_REDIS_URL", "redis://localhost:6379/0")
    )
