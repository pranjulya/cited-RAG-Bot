"""Liveness and readiness."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, TypedDict

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import text

router = APIRouter()

HealthStatus = Literal["ok"]
ReadyStatus = Literal["ok"]


class HealthResponse(TypedDict):
    status: HealthStatus


class ReadyResponse(TypedDict):
    status: ReadyStatus


@router.get("/health")
def health() -> HealthResponse:
    """Liveness: process is up. Does not check downstream dependencies."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> ReadyResponse:
    """Readiness: PostgreSQL and local storage are usable."""
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "reason": "database"},
        )
    try:
        async with factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "reason": "database"},
        ) from exc

    settings = request.app.state.settings
    storage_root = Path(settings.local_storage_path)
    try:
        storage_root.mkdir(parents=True, exist_ok=True)
        probe = storage_root / ".ready"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "reason": "storage"},
        ) from exc

    redis_url = getattr(settings, "redis_url", None)
    if redis_url:
        try:
            from redis.asyncio import Redis

            client = Redis.from_url(redis_url)
            try:
                await client.ping()
            finally:
                aclose = getattr(client, "aclose", None)
                if aclose is not None:
                    await aclose()
                else:
                    await client.close()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "not_ready", "reason": "redis"},
            ) from exc
    return {"status": "ok"}
