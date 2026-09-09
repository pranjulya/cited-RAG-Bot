from __future__ import annotations

from cited_rag.observability.correlation import get_correlation_id, set_correlation_id
from cited_rag.observability.metrics import InMemoryMetrics
from cited_rag.observability.redact import redact_text
from cited_rag.observability.stages import QUERY_STAGES
from cited_rag.observability.tracing import span, traces


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
