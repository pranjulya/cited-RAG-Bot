"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response

from cited_rag.adapters.embedding.hashing import HashEmbeddingProvider
from cited_rag.adapters.generation import create_generator
from cited_rag.adapters.persistence.postgres.session import create_engine, create_session_factory
from cited_rag.adapters.queue.arq_redis import ArqJobQueue
from cited_rag.adapters.queue.memory import MemoryJobQueue
from cited_rag.adapters.rerank import create_reranker
from cited_rag.adapters.retrieval.qdrant import QdrantRetrievalStore
from cited_rag.adapters.sparse import create_sparse_encoder
from cited_rag.adapters.storage.local import LocalObjectStorage
from cited_rag.api.health import router as health_router
from cited_rag.api.routes.collections import router as collections_router
from cited_rag.api.routes.documents import router as documents_router
from cited_rag.api.routes.query import router as query_router
from cited_rag.config import Settings, get_settings
from cited_rag.observability.correlation import CorrelationIdFilter, set_correlation_id

logger = logging.getLogger("cited_rag")


def _configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s correlation_id=%(correlation_id)s %(message)s",
    )
    # Logger filters are not applied to records that propagate from child loggers.
    # The formatter requires correlation_id, so the filter must live on handlers.
    correlation_filter = CorrelationIdFilter()
    for handler in logging.getLogger().handlers:
        if not any(isinstance(item, CorrelationIdFilter) for item in handler.filters):
            handler.addFilter(correlation_filter)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine = None
    if settings.database_url is not None:
        engine = create_engine(settings.database_url.get_secret_value())
        app.state.session_factory = create_session_factory(engine)
    app.state.storage = LocalObjectStorage(Path(settings.local_storage_path))
    queue: MemoryJobQueue | ArqJobQueue
    if settings.environment == "test" and not settings.redis_url:
        queue = MemoryJobQueue()
    elif settings.redis_url:
        queue = await ArqJobQueue.from_url(settings.redis_url)
    else:
        raise RuntimeError("CITED_RAG_REDIS_URL is required outside tests")
    app.state.queue = queue
    app.state.embedder = HashEmbeddingProvider(dimension=settings.embedding_dimension)
    app.state.sparse_encoder = create_sparse_encoder(settings)
    app.state.reranker = create_reranker(settings)
    app.state.generator = create_generator(settings)
    store = None
    if settings.qdrant_url:
        store = QdrantRetrievalStore(
            url=settings.qdrant_url, collection_name=settings.qdrant_collection
        )
    app.state.retrieval_store = store
    app.state.query_semaphore = asyncio.Semaphore(settings.max_in_flight_queries)
    logger.info("application starting")
    yield
    logger.info("application stopping")
    closer = getattr(queue, "close", None)
    if closer is not None:
        await closer()
    if store is not None:
        await store.close()
    if engine is not None:
        await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings if settings is not None else get_settings()
    _configure_logging(resolved)

    app = FastAPI(
        title="Cited RAG Bot",
        version="0.1.0",
        debug=resolved.debug,
        lifespan=_lifespan,
    )
    app.state.settings = resolved

    @app.middleware("http")
    async def add_correlation_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        header_name = resolved.correlation_id_header
        correlation_id = request.headers.get(header_name) or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        set_correlation_id(correlation_id)
        try:
            response = await call_next(request)
        finally:
            set_correlation_id("-")
        response.headers[header_name] = correlation_id
        return response

    app.include_router(health_router)
    app.include_router(collections_router)
    app.include_router(documents_router)
    app.include_router(query_router)
    return app


app = create_app()
