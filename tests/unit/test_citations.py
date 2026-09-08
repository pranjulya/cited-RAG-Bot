from __future__ import annotations

from uuid import uuid4

import pytest

from cited_rag.application.citations import validate_citations
from cited_rag.domain.enums import AnswerStatus
from cited_rag.domain.exceptions import CitationValidationError
from cited_rag.domain.models.evidence import EvidencePackage, EvidenceRecord
from cited_rag.domain.models.generation import Claim, GroundedGenerationResult


def _record(*, collection_id=None, version_id=None, evidence_id="E1") -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        chunk_id=uuid4(),
        collection_id=collection_id or uuid4(),
        document_id=uuid4(),
        document_version_id=version_id or uuid4(),
        document_name="handbook.pdf",
        page_start=17,
        page_end=17,
        text="Employees receive 20 days.",
    )


def _package(*records: EvidenceRecord) -> EvidencePackage:
    return EvidencePackage(records=records, model_context="ctx", dropped_chunk_ids=())


def _answered(*evidence_ids: str) -> GroundedGenerationResult:
    return GroundedGenerationResult(
        status=AnswerStatus.ANSWERED,
        answer="Employees receive 20 days.",
        claims=(Claim(text="Employees receive 20 days.", evidence_ids=evidence_ids),),
        model="heuristic-v1",
    )


def test_valid_citation_uses_server_provenance() -> None:
    record = _record()
    citations = validate_citations(
        _answered("E1"),
        _package(record),
        collection_id=record.collection_id,
        allowed_version_ids={record.document_version_id},
    )
    assert len(citations) == 1
    citation = citations[0]
    assert citation.document_id == record.document_id
    assert citation.document_version_id == record.document_version_id
    assert citation.document_name == "handbook.pdf"
    assert citation.page_start == 17
    assert citation.page_end == 17
    assert not hasattr(citation, "chunk_id")


def test_unknown_evidence_id_fails_closed() -> None:
    record = _record()
    with pytest.raises(CitationValidationError, match="unapproved"):
        validate_citations(
            _answered("E99"),
            _package(record),
            collection_id=record.collection_id,
        )


def test_cross_collection_evidence_fails() -> None:
    record = _record()
    with pytest.raises(CitationValidationError, match="collection"):
        validate_citations(
            _answered("E1"),
            _package(record),
            collection_id=uuid4(),
        )


def test_stale_version_fails() -> None:
    record = _record()
    with pytest.raises(CitationValidationError, match="searchable"):
        validate_citations(
            _answered("E1"),
            _package(record),
            collection_id=record.collection_id,
            allowed_version_ids={uuid4()},
        )


def test_duplicate_ids_are_normalized() -> None:
    record = _record()
    citations = validate_citations(
        GroundedGenerationResult(
            status=AnswerStatus.ANSWERED,
            answer="x",
            claims=(
                Claim(text="a", evidence_ids=("E1", "E1")),
                Claim(text="b", evidence_ids=("E1",)),
            ),
            model="heuristic-v1",
        ),
        _package(record),
        collection_id=record.collection_id,
    )
    assert len(citations) == 1


def test_insufficient_evidence_with_no_claims_is_empty() -> None:
    record = _record()
    citations = validate_citations(
        GroundedGenerationResult(
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            answer="not enough",
            claims=(),
            model="heuristic-v1",
        ),
        _package(record),
        collection_id=record.collection_id,
    )
    assert citations == ()


def test_insufficient_with_invented_id_still_fails() -> None:
    record = _record()
    with pytest.raises(CitationValidationError):
        validate_citations(
            GroundedGenerationResult(
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                answer="not enough",
                claims=(Claim(text="x", evidence_ids=("E99",)),),
                model="heuristic-v1",
            ),
            _package(record),
            collection_id=record.collection_id,
        )
