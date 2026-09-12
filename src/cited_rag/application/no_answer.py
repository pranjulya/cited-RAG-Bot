from __future__ import annotations

from collections.abc import Sequence

from cited_rag.domain.enums import AnswerStatus, NoAnswerReason
from cited_rag.domain.models.evidence import EvidencePackage
from cited_rag.domain.models.generation import GroundedGenerationResult
from cited_rag.domain.models.policy import NoAnswerDecision
from cited_rag.domain.models.retrieval import FusedCandidate, RerankedEvidence

DEFAULT_NO_ANSWER_MESSAGE = (
    "The available documents do not provide enough evidence to answer this question."
)


def no_ready_documents() -> NoAnswerDecision:
    return NoAnswerDecision(reason=NoAnswerReason.NO_READY_DOCUMENTS)


def decide_before_generation(
    *,
    fused: Sequence[FusedCandidate],
    reranked: Sequence[RerankedEvidence],
    evidence: EvidencePackage,
    min_rerank_score: float,
) -> NoAnswerDecision | None:
    if not fused:
        return NoAnswerDecision(reason=NoAnswerReason.NO_RETRIEVAL_RESULTS)
    if not reranked:
        return NoAnswerDecision(reason=NoAnswerReason.WEAK_EVIDENCE)
    best = max(item.rerank_score for item in reranked)
    if best < min_rerank_score:
        return NoAnswerDecision(reason=NoAnswerReason.WEAK_EVIDENCE)
    if not evidence.records:
        return NoAnswerDecision(reason=NoAnswerReason.CONTEXT_EMPTY)
    return None


def decide_after_generation(result: GroundedGenerationResult) -> NoAnswerDecision | None:
    if result.status is AnswerStatus.INSUFFICIENT_EVIDENCE:
        return NoAnswerDecision(reason=NoAnswerReason.MODEL_ABSTENTION)
    return None
