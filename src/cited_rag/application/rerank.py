from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Sequence

from cited_rag.domain.exceptions import RerankerError
from cited_rag.domain.models.evaluation import EvaluationRunConfig
from cited_rag.domain.models.retrieval import FusedCandidate, RerankedEvidence
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
            extra={"correlation_id": "-"},
        )
        return passthrough
    if not candidates or top_n < 1:
        logger.info(
            "rerank empty count=0 top_n=%s",
            top_n,
            extra={"correlation_id": "-"},
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
    logger.info(
        "rerank count=%s top_n=%s latency_ms=%s",
        len(ranked),
        top_n,
        int((time.perf_counter() - started) * 1000),
        extra={"correlation_id": "-"},
    )
    return ranked


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
