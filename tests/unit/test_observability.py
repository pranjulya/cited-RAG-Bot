from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

import pytest

from cited_rag.application.retrieval.retrievers import retrieve_dense
from cited_rag.observability.correlation import get_correlation_id, set_correlation_id
from cited_rag.observability.metrics import InMemoryMetrics
from cited_rag.observability.redact import redact_text
from cited_rag.observability.stages import QUERY_STAGES
from cited_rag.observability.tracing import span, traces


def test_set_correlation_id_is_readable() -> None:
    set_correlation_id("abc")
    assert get_correlation_id() == "abc"
    set_correlation_id("-")


def test_application_logs_do_not_hardcode_blank_correlation_id() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "cited_rag" / "application"
    offenders = [
        str(path.relative_to(root.parents[2]))
        for path in root.rglob("*.py")
        if 'extra={"correlation_id": "-"}' in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


@pytest.mark.asyncio
async def test_retrieval_log_extra_uses_context_correlation_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    set_correlation_id("abc")
    with caplog.at_level(logging.INFO, logger="cited_rag.retrieval"):
        await retrieve_dense(
            "unused",
            embedder=object(),  # type: ignore[arg-type]
            store=object(),  # type: ignore[arg-type]
            collection_id=uuid4(),
            document_version_ids=[],
            top_k=5,
        )
    set_correlation_id("-")
    extras = [
        record.correlation_id
        for record in caplog.records
        if getattr(record, "correlation_id", None)
    ]
    assert "abc" in extras


def test_redact_hides_raw_content_by_default() -> None:
    raw = "Employees receive 20 days of leave."
    redacted = redact_text(raw)
    assert "Employees" not in redacted
    assert "chars=" in redacted
    assert redact_text(raw, enabled=False) == raw


def test_metrics_increment_without_high_cardinality_labels() -> None:
    meters = InMemoryMetrics()
    meters.incr("query.no_answer")
    meters.incr("query.no_answer")
    meters.incr("citation.validation_failed")
    assert meters.get("query.no_answer") == 2
    assert "query.request" in QUERY_STAGES
    assert "query.citation_validate" in QUERY_STAGES


def test_span_records_name_duration_and_correlation() -> None:
    traces.clear()
    set_correlation_id("trace-9")
    with span("query.rerank"):
        assert get_correlation_id() == "trace-9"
    recorded = traces.spans[-1]
    assert recorded.name == "query.rerank"
    assert recorded.status == "ok"
    assert recorded.correlation_id == "trace-9"
    assert recorded.duration_ms >= 0
    set_correlation_id("-")
