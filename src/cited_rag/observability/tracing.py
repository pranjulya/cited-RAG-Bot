from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from cited_rag.observability.correlation import get_correlation_id
from cited_rag.observability.metrics import metrics

logger = logging.getLogger("cited_rag.trace")


@dataclass
class Span:
    name: str
    duration_ms: int = 0
    status: str = "ok"
    correlation_id: str = "-"


@dataclass
class TraceBuffer:
    spans: list[Span] = field(default_factory=list)

    def clear(self) -> None:
        self.spans.clear()


traces = TraceBuffer()
_trace_buffer: ContextVar[list[Span] | None] = ContextVar("trace_buffer", default=None)


def start_trace() -> None:
    _trace_buffer.set([])


def take_trace() -> list[Span]:
    records = _trace_buffer.get() or []
    _trace_buffer.set(None)
    return list(records)


@contextmanager
def span(name: str) -> Iterator[Span]:
    record = Span(name=name, correlation_id=get_correlation_id())
    started = time.perf_counter()
    try:
        yield record
    except Exception:
        record.status = "error"
        raise
    finally:
        record.duration_ms = int((time.perf_counter() - started) * 1000)
        traces.spans.append(record)
        buffer = _trace_buffer.get()
        if buffer is not None:
            buffer.append(record)
        metrics.incr(f"span.{name}")
        logger.info(
            "span name=%s duration_ms=%s status=%s",
            record.name,
            record.duration_ms,
            record.status,
            extra={"correlation_id": record.correlation_id},
        )
