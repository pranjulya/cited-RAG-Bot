from __future__ import annotations

import os
from pathlib import Path
from typing import cast
from uuid import UUID

from arq import Retry
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from cited_rag.adapters.chunking import create_chunker
from cited_rag.adapters.parser import create_document_parser
from cited_rag.adapters.persistence.postgres.session import create_engine, create_session_factory
from cited_rag.adapters.persistence.postgres.uow import PostgresUnitOfWork
from cited_rag.adapters.storage.local import LocalObjectStorage
from cited_rag.application.ingestion import process_ingestion_job
from cited_rag.config import get_settings
from cited_rag.ports.chunker import Chunker
from cited_rag.ports.object_storage import ObjectStorage
from cited_rag.ports.parser import DocumentParser


async def ingest_document_version(
    ctx: dict[str, object],
    document_version_id: str,
    correlation_id: str | None = None,
) -> str:
    factory = ctx["session_factory"]
    assert isinstance(factory, async_sessionmaker)
    storage = cast(ObjectStorage, ctx["storage"])
    parser = cast(DocumentParser, ctx["parser"])
    chunker = cast(Chunker, ctx["chunker"])
    settings = get_settings()
    async with PostgresUnitOfWork(factory) as uow:
        outcome = await process_ingestion_job(
            uow,
            document_version_id=UUID(document_version_id),
            correlation_id=correlation_id,
            max_attempts=settings.ingestion_max_attempts,
            lease_seconds=settings.ingestion_lease_seconds,
            storage=storage,
            parser=parser,
            chunker=chunker,
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
    ctx["storage"] = LocalObjectStorage(Path(settings.local_storage_path))
    ctx["parser"] = create_document_parser(settings.parser_backend)
    ctx["chunker"] = create_chunker(settings)


async def shutdown(ctx: dict[str, object]) -> None:
    engine = ctx.get("engine")
    if isinstance(engine, AsyncEngine):
        await engine.dispose()


class WorkerSettings:
    functions = [ingest_document_version]
    on_startup = startup
    on_shutdown = shutdown
    max_tries = 10
    job_timeout = 300
    redis_settings = RedisSettings.from_dsn(
        os.environ.get("CITED_RAG_REDIS_URL", "redis://localhost:6379/0")
    )
