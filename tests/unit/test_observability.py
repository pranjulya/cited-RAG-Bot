from __future__ import annotations

from cited_rag.observability.metrics import InMemoryMetrics
from cited_rag.observability.redact import redact_text
from cited_rag.observability.stages import QUERY_STAGES


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
