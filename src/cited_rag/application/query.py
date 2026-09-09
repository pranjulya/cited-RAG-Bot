from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from uuid import UUID

from cited_rag.application.citations import validate_citations
from cited_rag.application.context import build_evidence_package
from cited_rag.application.generation import generate_grounded_answer
from cited_rag.application.no_answer import (
    decide_after_generation,
    decide_before_generation,
    no_ready_documents,
)
from cited_rag.application.rerank import rerank_candidates
from cited_rag.application.retrieval import ReciprocalRankFusion, retrieve_hybrid
from cited_rag.application.retrieval.retrievers import ChunkLoader
from cited_rag.config import Settings
from cited_rag.domain.enums import AnswerStatus
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.evaluation import EvaluationRunConfig
from cited_rag.domain.models.policy import NoAnswerDecision
from cited_rag.domain.models.query_result import QueryOutcome
from cited_rag.observability.correlation import get_correlation_id, set_correlation_id
from cited_rag.observability.metrics import metrics
from cited_rag.observability.redact import redact_text
from cited_rag.observability.tracing import span
from cited_rag.ports.embedding import EmbeddingProvider
from cited_rag.ports.generation import GroundedGenerator
from cited_rag.ports.reranker import Reranker
from cited_rag.ports.retrieval_store import RetrievalStore
from cited_rag.ports.sparse_encoder import SparseEncoder

logger = logging.getLogger("cited_rag.query")


def _from_decision(decision: NoAnswerDecision) -> QueryOutcome:
    return QueryOutcome(
        status=AnswerStatus.INSUFFICIENT_EVIDENCE,
        answer=decision.message,
        citations=(),
        reason=decision.reason,
    )


async def answer_question(
    question: str,
    *,
    collection_id: UUID,
    document_version_ids: Sequence[UUID],
    chunks: Sequence[Chunk] = (),
    document_names: Mapping[UUID, str] | None = None,
    load_chunks: ChunkLoader | None = None,
    embedder: EmbeddingProvider,
    encoder: SparseEncoder,
    store: RetrievalStore,
    reranker: Reranker,
    generator: GroundedGenerator,
    settings: Settings,
    evaluation: EvaluationRunConfig | None = None,
    correlation_id: str | None = None,
) -> QueryOutcome:
    """Collection-scoped query pipeline. Routes own authorization."""
    if correlation_id:
        set_correlation_id(correlation_id)
    cid = get_correlation_id()
    stripped = question.strip()
    logger.info(
        "query start collection=%s versions=%s question=%s",
        collection_id,
        len(document_version_ids),
        redact_text(stripped, enabled=not getattr(settings, "log_sensitive_content", False)),
        extra={"correlation_id": cid},
    )
    metrics.incr("query.started")
    with span("query.request"):
        if not document_version_ids:
            metrics.incr("query.no_answer")
            return _from_decision(no_ready_documents())
        with span("query.fusion"):
            fused = await retrieve_hybrid(
                stripped,
                embedder=embedder,
                encoder=encoder,
                store=store,
                chunks=chunks,
                collection_id=collection_id,
                document_version_ids=document_version_ids,
                top_k=settings.retrieval_top_k,
                fusion=ReciprocalRankFusion(k=settings.rrf_k),
                fused_top_k=settings.fused_top_k,
                evaluation=evaluation,
                load_chunks=load_chunks,
            )
        with span("query.rerank"):
            reranked = await rerank_candidates(
                stripped,
                fused,
                reranker=reranker,
                top_n=settings.rerank_top_n,
                timeout_seconds=settings.reranker_timeout_seconds,
                evaluation=evaluation,
            )
        with span("query.context_build"):
            evidence = build_evidence_package(
                reranked,
                max_items=settings.max_evidence_items,
                token_budget=settings.context_token_budget,
                document_names=document_names or {},
            )
        before = decide_before_generation(
            fused=fused,
            reranked=reranked,
            evidence=evidence,
            min_rerank_score=settings.min_rerank_score,
        )
        if before is not None:
            metrics.incr("query.no_answer")
            return _from_decision(before)
        with span("query.generation"):
            generated = await generate_grounded_answer(
                stripped,
                evidence,
                generator=generator,
                timeout_seconds=settings.generation_timeout_seconds,
            )
        after = decide_after_generation(generated)
        if after is not None:
            metrics.incr("query.no_answer")
            with span("query.citation_validate"):
                citations = validate_citations(
                    generated,
                    evidence,
                    collection_id=collection_id,
                    allowed_version_ids=set(document_version_ids),
                )
            return QueryOutcome(
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                answer=after.message,
                citations=citations,
                reason=after.reason,
            )
        with span("query.citation_validate"):
            citations = validate_citations(
                generated,
                evidence,
                collection_id=collection_id,
                allowed_version_ids=set(document_version_ids),
            )
        metrics.incr("query.answered")
        logger.info(
            "query complete status=%s citations=%s",
            generated.status,
            len(citations),
            extra={"correlation_id": cid},
        )
        return QueryOutcome(
            status=generated.status,
            answer=generated.answer,
            citations=citations,
            reason=None,
        )
