"""Liveness and Phase 00 readiness skeleton."""

from __future__ import annotations

from typing import Literal, TypedDict

from fastapi import APIRouter

router = APIRouter()

HealthStatus = Literal["ok"]
ReadyStatus = Literal["not_configured"]


class HealthResponse(TypedDict):
    status: HealthStatus


class ReadyResponse(TypedDict):
    status: ReadyStatus


@router.get("/health")
def health() -> HealthResponse:
    """Liveness: process is up. Does not check downstream dependencies."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> ReadyResponse:
    """Phase 00 readiness skeleton. HTTP 200 with this body until later phases add checks."""
    return {"status": "not_configured"}
