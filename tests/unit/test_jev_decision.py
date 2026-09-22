from __future__ import annotations

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from cited_rag.domain.models.decision import EvidenceDecision
from cited_rag.domain.models.evidence import EvidenceRecord


def test_evidence_decision_is_immutable_and_normalized() -> None:
    decision = EvidenceDecision(
        answerable_probability=0.8,
        model="typesafe/jev-1.13",
    )

    assert decision.answerable is True
    assert decision.answerable_probability == 0.8
    assert decision.model == "typesafe/jev-1.13"
    with pytest.raises(FrozenInstanceError):
        decision.model = "other"  # type: ignore[misc]


@pytest.mark.parametrize("probability", [-0.01, 1.01])
def test_evidence_decision_rejects_probability_outside_unit_interval(
    probability: float,
) -> None:
    with pytest.raises(ValueError, match="probability"):
        EvidenceDecision(answerable_probability=probability, model="jev")


def test_evidence_record_has_provenance_but_adapter_input_can_be_narrowed() -> None:
    record = EvidenceRecord(
        evidence_id="E1",
        chunk_id=uuid4(),
        collection_id=uuid4(),
        document_id=uuid4(),
        document_version_id=uuid4(),
        document_name="handbook.pdf",
        page_start=2,
        page_end=2,
        text="Employees receive 20 days of leave.",
    )

    assert record.evidence_id == "E1"
    assert record.text.startswith("Employees")
