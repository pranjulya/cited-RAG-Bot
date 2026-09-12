from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Sequence
from uuid import UUID

from cited_rag.domain.exceptions import RerankerError
from cited_rag.domain.models.evaluation import EvaluationRunConfig
from cited_rag.domain.models.retrieval import FusedCandidate, RerankedEvidence
from cited_rag.observability.correlation import get_correlation_id
from cited_rag.ports.reranker import Reranker

logger = logging.getLogger("cited_rag.rerank")


async def rerank_candidates(
    query: str,
    candidates: Sequence[FusedCandidate],
    *,
    reranker: Reranker,
    top_n: int,
    timeout_seconds: float,
    evaluation: EvaluationRunConfig | None = None,
) -> list[RerankedEvidence]:
    started = time.perf_counter()
    if evaluation is not None and not evaluation.include_rerank:
        passthrough = _passthrough(candidates, top_n)
        logger.info(
            "rerank disabled count=%s top_n=%s latency_ms=%s",
            len(passthrough),
            top_n,
            int((time.perf_counter() - started) * 1000),
            extra={"correlation_id": get_correlation_id()},
        )
        return passthrough
    if not candidates or top_n < 1:
        logger.info(
            "rerank empty count=0 top_n=%s",
            top_n,
            extra={"correlation_id": get_correlation_id()},
        )
        return []
    try:
        ranked = await asyncio.wait_for(
            reranker.rerank(query, candidates, top_n),
            timeout=timeout_seconds,
        )
    except RerankerError:
        raise
    except TimeoutError as exc:
        raise RerankerError(str(exc) or "reranker timed out") from exc
    except Exception as exc:
        raise RerankerError("reranker failed") from exc
    validated = _validated_rerank(ranked, candidates, top_n=top_n)
    logger.info(
        "rerank count=%s top_n=%s latency_ms=%s",
        len(validated),
        top_n,
        int((time.perf_counter() - started) * 1000),
        extra={"correlation_id": get_correlation_id()},
    )
    return validated


def _validated_rerank(
    ranked: Sequence[RerankedEvidence],
    candidates: Sequence[FusedCandidate],
    *,
    top_n: int,
) -> list[RerankedEvidence]:
    by_id = {item.chunk_id: item for item in candidates}
    seen: set[UUID] = set()
    if len(ranked) > top_n:
        raise RerankerError("reranker returned more than top_n candidates")
    validated: list[RerankedEvidence] = []
    for rank, item in enumerate(ranked, start=1):
        source = by_id.get(item.chunk_id)
        if source is None:
            raise RerankerError("reranker returned an unknown chunk")
        if item.chunk_id in seen:
            raise RerankerError("reranker returned a duplicate chunk")
        seen.add(item.chunk_id)
        if (
            item.collection_id != source.collection_id
            or item.document_id != source.document_id
            or item.document_version_id != source.document_version_id
            or item.page_start != source.page_start
            or item.page_end != source.page_end
            or item.text != source.text
            or item.fused_rank != source.fused_rank
            or item.rrf_score != source.rrf_score
        ):
            raise RerankerError("reranker payload does not match fused candidate")
        if item.rerank_rank != rank:
            raise RerankerError("reranker ranks are malformed")
        validated.append(item)
    return validated


def _passthrough(candidates: Sequence[FusedCandidate], top_n: int) -> list[RerankedEvidence]:
    if top_n < 1:
        return []
    return [
        RerankedEvidence(
            chunk_id=candidate.chunk_id,
            rerank_score=candidate.rrf_score,
            rerank_rank=rank,
            fused_rank=candidate.fused_rank,
            rrf_score=candidate.rrf_score,
            collection_id=candidate.collection_id,
            document_id=candidate.document_id,
            document_version_id=candidate.document_version_id,
            page_start=candidate.page_start,
            page_end=candidate.page_end,
            text=candidate.text,
            dense_rank=candidate.dense_rank,
            dense_score=candidate.dense_score,
            sparse_rank=candidate.sparse_rank,
            sparse_score=candidate.sparse_score,
            reranker_name="disabled",
            reranker_version="evaluation",
        )
        for rank, candidate in enumerate(candidates[:top_n], start=1)
    ]
