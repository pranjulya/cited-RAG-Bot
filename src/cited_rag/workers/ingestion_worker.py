from __future__ import annotations

import os
from pathlib import Path
from typing import cast
from uuid import UUID

from arq import Retry
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from cited_rag.adapters.chunking import create_chunker
from cited_rag.adapters.embedding import create_embedding_provider
from cited_rag.adapters.parser import create_document_parser
from cited_rag.adapters.persistence.postgres.session import create_engine, create_session_factory
from cited_rag.adapters.persistence.postgres.uow import PostgresUnitOfWork
from cited_rag.adapters.retrieval import create_retrieval_store
from cited_rag.adapters.sparse import create_sparse_encoder
from cited_rag.adapters.storage.local import LocalObjectStorage
from cited_rag.application.ingestion import process_ingestion_job
from cited_rag.config import get_settings
from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.ports.chunker import Chunker
from cited_rag.ports.embedding import EmbeddingProvider
from cited_rag.ports.object_storage import ObjectStorage
from cited_rag.ports.parser import DocumentParser
from cited_rag.ports.retrieval_store import RetrievalStore
from cited_rag.ports.sparse_encoder import SparseEncoder


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
    embedding_provider = cast(EmbeddingProvider, ctx["embedding_provider"])
    retrieval_store = cast(RetrievalStore, ctx["retrieval_store"])
    embedding_config = cast(EmbeddingConfig, ctx["embedding_config"])
    sparse_encoder = cast(SparseEncoder, ctx["sparse_encoder"])
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
            embedding_provider=embedding_provider,
            retrieval_store=retrieval_store,
            embedding_config=embedding_config,
            sparse_encoder=sparse_encoder,
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
    ctx["embedding_provider"] = create_embedding_provider(settings)
    ctx["retrieval_store"] = create_retrieval_store(settings)
    ctx["embedding_config"] = EmbeddingConfig(
        dimension=settings.embedding_dimension,
        batch_size=settings.embedding_batch_size,
        model=settings.embedding_model,
        index_version=settings.index_version,
    )
    ctx["sparse_encoder"] = create_sparse_encoder(settings)


async def shutdown(ctx: dict[str, object]) -> None:
    store = ctx.get("retrieval_store")
    closer = getattr(store, "close", None)
    if closer is not None:
        await closer()
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
