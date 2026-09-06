"""FastAPI application factory."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path

from fastapi import FastAPI, Request, Response

from cited_rag.adapters.persistence.postgres.session import create_engine, create_session_factory
from cited_rag.adapters.queue.arq_redis import ArqJobQueue
from cited_rag.adapters.queue.memory import MemoryJobQueue
from cited_rag.adapters.storage.local import LocalObjectStorage
from cited_rag.api.health import router as health_router
from cited_rag.api.routes.collections import router as collections_router
from cited_rag.api.routes.documents import router as documents_router
from cited_rag.config import Settings, get_settings

logger = logging.getLogger("cited_rag")
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def _configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s correlation_id=%(correlation_id)s %(message)s",
    )
    # Logger filters are not applied to records that propagate from child loggers.
    # The formatter requires correlation_id, so the filter must live on handlers.
    correlation_filter = _CorrelationIdFilter()
    for handler in logging.getLogger().handlers:
        if not any(isinstance(item, _CorrelationIdFilter) for item in handler.filters):
            handler.addFilter(correlation_filter)


class _CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = _correlation_id.get()
        return True


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
    logger.info("application starting")
    yield
    logger.info("application stopping")
    closer = getattr(queue, "close", None)
    if closer is not None:
        await closer()
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
        token = _correlation_id.set(correlation_id)
        try:
            response = await call_next(request)
        finally:
            _correlation_id.reset(token)
        response.headers[header_name] = correlation_id
        return response

    app.include_router(health_router)
    app.include_router(collections_router)
    app.include_router(documents_router)
    return app


app = create_app()
