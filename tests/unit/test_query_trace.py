from __future__ import annotations

from uuid import uuid4

from cited_rag.api.routes.query import _trace_body
from cited_rag.config import Settings
from cited_rag.domain.models.evidence import EvidenceRecord
from cited_rag.observability.tracing import Span


def test_trace_body_orders_six_stages_and_truncates_evidence() -> None:
    record = EvidenceRecord(
        evidence_id="E1",
        chunk_id=uuid4(),
        collection_id=uuid4(),
        document_id=uuid4(),
        document_version_id=uuid4(),
        document_name="policy.pdf",
        page_start=1,
        page_end=1,
        text="abcdef",
    )
    body = _trace_body(
        spans=[Span(name="query.fusion", duration_ms=3)],
        evidence=(record,),
        correlation_id="corr-1",
        settings=Settings(_env_file=None, trace_evidence_chars=5),
    )

    assert [stage.name for stage in body.stages] == [
        "query.request",
        "query.fusion",
        "query.rerank",
        "query.context_build",
        "query.generation",
        "query.citation_validate",
    ]
    assert body.stages[0].status == "skipped"
    assert body.stages[1].duration_ms == 3
    assert body.evidence[0].id == "E1"
    assert body.evidence[0].text == "abcde"
    assert body.evidence[0].truncated is True
    assert not hasattr(body.evidence[0], "chunk_id")
    assert body.correlation_id == "corr-1"
