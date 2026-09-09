from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Sequence
from uuid import UUID

from cited_rag.application.retrieval.fusion import FusionStrategy
from cited_rag.application.retrieval.retrievers import retrieve_dense, retrieve_sparse
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.evaluation import EvaluationRunConfig
from cited_rag.domain.models.retrieval import FusedCandidate, RetrievedCandidate
from cited_rag.ports.embedding import EmbeddingProvider
from cited_rag.ports.retrieval_store import RetrievalStore
from cited_rag.ports.sparse_encoder import SparseEncoder

logger = logging.getLogger("cited_rag.retrieval")


async def retrieve_hybrid(
    query: str,
    *,
    embedder: EmbeddingProvider,
    encoder: SparseEncoder,
    store: RetrievalStore,
    chunks: Sequence[Chunk],
    collection_id: UUID,
    document_version_ids: Sequence[UUID],
    top_k: int,
    fusion: FusionStrategy,
    fused_top_k: int,
    evaluation: EvaluationRunConfig | None = None,
) -> list[FusedCandidate]:
    """Run dense and sparse independently, then fuse ranks in process.

    Production callers omit `evaluation` so both retrievers always run.
    Ablations use EvaluationRunConfig; that is not a production fallback.
    """
    started = time.perf_counter()
    run = evaluation if evaluation is not None else EvaluationRunConfig()
    if not run.include_dense and not run.include_sparse:
        raise ValueError("evaluation run must include dense or sparse retrieval")

    async def _dense() -> list[RetrievedCandidate]:
        if not run.include_dense:
            return []
        return await retrieve_dense(
            query,
            embedder=embedder,
            store=store,
            chunks=chunks,
            collection_id=collection_id,
            document_version_ids=document_version_ids,
            top_k=top_k,
        )

    async def _sparse() -> list[RetrievedCandidate]:
        if not run.include_sparse:
            return []
        return await retrieve_sparse(
            query,
            encoder=encoder,
            store=store,
            chunks=chunks,
            collection_id=collection_id,
            document_version_ids=document_version_ids,
            top_k=top_k,
        )

    dense, sparse = await asyncio.gather(_dense(), _sparse())
    fused = fusion.fuse(dense, sparse, limit=fused_top_k)
    logger.info(
        "hybrid retrieval dense=%s sparse=%s fused=%s top_k=%s fused_top_k=%s latency_ms=%s",
        len(dense),
        len(sparse),
        len(fused),
        top_k,
        fused_top_k,
        int((time.perf_counter() - started) * 1000),
        extra={"correlation_id": "-"},
    )
    return fused
