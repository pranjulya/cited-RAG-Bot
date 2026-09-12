from __future__ import annotations

import re
from collections.abc import Sequence

from cited_rag.domain.exceptions import RerankerError
from cited_rag.domain.models.retrieval import FusedCandidate, RerankedEvidence

_TOKEN = re.compile(r"[A-Za-z0-9_]+")

OVERLAP_RERANKER_NAME = "lexical-overlap"
OVERLAP_RERANKER_VERSION = "v1"


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN.findall(text)}


class LexicalOverlapReranker:
    """Deterministic overlap scorer for tests/dev. Not a cross-encoder."""

    name = OVERLAP_RERANKER_NAME
    version = OVERLAP_RERANKER_VERSION

    async def rerank(
        self,
        query: str,
        candidates: Sequence[FusedCandidate],
        top_n: int,
    ) -> list[RerankedEvidence]:
        if top_n < 1:
            return []
        query_tokens = _tokens(query)
        scored: list[tuple[float, FusedCandidate]] = []
        for candidate in candidates:
            if not candidate.text.strip():
                raise RerankerError("reranker candidate text is missing")
            overlap = float(len(query_tokens & _tokens(candidate.text)))
            scored.append((overlap, candidate))
        scored.sort(key=lambda item: (-item[0], item[1].fused_rank, str(item[1].chunk_id)))
        return [
            RerankedEvidence(
                chunk_id=candidate.chunk_id,
                rerank_score=score,
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
                reranker_name=self.name,
                reranker_version=self.version,
            )
            for rank, (score, candidate) in enumerate(scored[:top_n], start=1)
        ]
