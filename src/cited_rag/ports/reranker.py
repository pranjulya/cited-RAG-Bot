from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from cited_rag.domain.models.retrieval import FusedCandidate, RerankedEvidence


class Reranker(Protocol):
    async def rerank(
        self,
        query: str,
        candidates: Sequence[FusedCandidate],
        top_n: int,
    ) -> list[RerankedEvidence]: ...
