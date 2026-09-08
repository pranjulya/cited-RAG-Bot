from __future__ import annotations

from uuid import uuid4

from cited_rag.application.no_answer import (
    decide_after_generation,
    decide_before_generation,
    no_ready_documents,
)
from cited_rag.domain.enums import AnswerStatus, NoAnswerReason
from cited_rag.domain.exceptions import GenerationError
from cited_rag.domain.models.evidence import EvidencePackage, EvidenceRecord
from cited_rag.domain.models.generation import Claim, GroundedGenerationResult
from cited_rag.domain.models.retrieval import FusedCandidate, RerankedEvidence


def _fused() -> FusedCandidate:
    return FusedCandidate(
        chunk_id=uuid4(),
        rrf_score=0.2,
        fused_rank=1,
        collection_id=uuid4(),
        document_id=uuid4(),
        document_version_id=uuid4(),
        page_start=1,
        page_end=1,
        text="Employees receive 20 days of leave.",
        dense_rank=1,
        dense_score=1.0,
        sparse_rank=None,
        sparse_score=None,
    )


def _reranked(score: float) -> RerankedEvidence:
    item = _fused()
    return RerankedEvidence(
        chunk_id=item.chunk_id,
        rerank_score=score,
        rerank_rank=1,
        fused_rank=1,
        rrf_score=item.rrf_score,
        collection_id=item.collection_id,
        document_id=item.document_id,
        document_version_id=item.document_version_id,
        page_start=1,
        page_end=1,
        text=item.text,
        dense_rank=1,
        dense_score=1.0,
        sparse_rank=None,
        sparse_score=None,
        reranker_name="lexical-overlap",
        reranker_version="v1",
    )


def _evidence() -> EvidencePackage:
    item = _reranked(2.0)
    record = EvidenceRecord(
        evidence_id="E1",
        chunk_id=item.chunk_id,
        collection_id=item.collection_id,
        document_id=item.document_id,
        document_version_id=item.document_version_id,
        document_name="handbook.pdf",
        page_start=1,
        page_end=1,
        text=item.text,
    )
    return EvidencePackage(records=(record,), model_context="E1", dropped_chunk_ids=())


def test_zero_ready_documents_is_insufficient_not_error() -> None:
    decision = no_ready_documents()
    assert decision.reason is NoAnswerReason.NO_READY_DOCUMENTS


def test_empty_retrieval_is_no_retrieval_results() -> None:
    decision = decide_before_generation(
        fused=[],
        reranked=[],
        evidence=EvidencePackage(records=(), model_context="", dropped_chunk_ids=()),
        min_rerank_score=0,
    )
    assert decision is not None
    assert decision.reason is NoAnswerReason.NO_RETRIEVAL_RESULTS


def test_weak_rerank_score_is_insufficient() -> None:
    fused = [_fused()]
    reranked = [_reranked(0.2)]
    decision = decide_before_generation(
        fused=fused,
        reranked=reranked,
        evidence=_evidence(),
        min_rerank_score=1.0,
    )
    assert decision is not None
    assert decision.reason is NoAnswerReason.WEAK_EVIDENCE


def test_empty_context_after_budget_is_insufficient() -> None:
    decision = decide_before_generation(
        fused=[_fused()],
        reranked=[_reranked(2.0)],
        evidence=EvidencePackage(records=(), model_context="", dropped_chunk_ids=()),
        min_rerank_score=0,
    )
    assert decision is not None
    assert decision.reason is NoAnswerReason.CONTEXT_EMPTY


def test_answerable_question_continues() -> None:
    decision = decide_before_generation(
        fused=[_fused()],
        reranked=[_reranked(2.0)],
        evidence=_evidence(),
        min_rerank_score=0,
    )
    assert decision is None


def test_model_abstention_is_insufficient() -> None:
    result = GroundedGenerationResult(
        status=AnswerStatus.INSUFFICIENT_EVIDENCE,
        answer="not enough",
        claims=(),
        model="heuristic-v1",
    )
    decision = decide_after_generation(result)
    assert decision is not None
    assert decision.reason is NoAnswerReason.MODEL_ABSTENTION


def test_provider_timeout_is_not_a_no_answer_reason() -> None:
    try:
        raise GenerationError("generation timed out")
    except GenerationError as exc:
        assert exc.failure_code == "GENERATION_PROVIDER_ERROR"
        assert (
            decide_after_generation(
                GroundedGenerationResult(
                    status=AnswerStatus.ANSWERED,
                    answer="ok",
                    claims=(Claim(text="ok", evidence_ids=("E1",)),),
                    model="heuristic-v1",
                )
            )
            is None
        )
        assert "INSUFFICIENT" not in exc.failure_code
