"""FastAPI application factory. No RAG behavior in Phase 00."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from cited_rag.api.health import router as health_router
from cited_rag.config import Settings, get_settings

logger = logging.getLogger("cited_rag")


def _configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s correlation_id=%(correlation_id)s %(message)s",
    )
    logging.getLogger().addFilter(_CorrelationIdFilter())


class _CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "-"
        return True


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("application starting")
    yield
    logger.info("application stopping")


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
        response = await call_next(request)
        response.headers[header_name] = correlation_id
        return response

    app.include_router(health_router)
    return app


app = create_app()
