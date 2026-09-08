from __future__ import annotations

_MAX = 48


def redact_text(value: str | None, *, enabled: bool = True) -> str:
    """Default: do not emit raw PDF/query content in logs."""
    if not value:
        return ""
    if not enabled:
        return value
    return f"[redacted chars={len(value)}]"


def clip_for_debug(value: str, *, limit: int = _MAX) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "…"
