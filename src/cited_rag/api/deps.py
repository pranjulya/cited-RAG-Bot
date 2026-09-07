from __future__ import annotations

import hmac
from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cited_rag.adapters.persistence.postgres.uow import PostgresUnitOfWork
from cited_rag.application.upload import ensure_principal
from cited_rag.config import Settings
from cited_rag.domain.models.principal import ApiPrincipal
from cited_rag.ports.object_storage import ObjectStorage
from cited_rag.ports.queue import JobQueue

_bearer = HTTPBearer(auto_error=False)


def _bearer_matches(provided: str, expected: str) -> bool:
    try:
        return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))
    except (TypeError, UnicodeError):
        return False


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


async def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings_dep),
) -> None:
    expected = settings.api_key.get_secret_value() if settings.api_key is not None else ""
    provided = credentials.credentials if credentials is not None else ""
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not expected
        or not _bearer_matches(provided, expected)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_uow(
    request: Request, _: None = Depends(require_api_key)
) -> AsyncIterator[PostgresUnitOfWork]:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database_not_configured"
        )
    async with PostgresUnitOfWork(factory) as uow:
        yield uow


async def get_principal(uow: PostgresUnitOfWork = Depends(get_uow)) -> ApiPrincipal:
    return await ensure_principal(uow)


def get_storage(request: Request) -> ObjectStorage:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="storage_not_configured"
        )
    return storage  # type: ignore[no-any-return]


def get_queue(request: Request) -> JobQueue:
    queue = getattr(request.app.state, "queue", None)
    if queue is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="queue_not_configured"
        )
    return queue  # type: ignore[no-any-return]
