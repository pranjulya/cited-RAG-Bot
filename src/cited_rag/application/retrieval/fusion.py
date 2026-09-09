from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from cited_rag.domain.exceptions import HybridFusionError
from cited_rag.domain.models.retrieval import FusedCandidate, RetrievedCandidate


class FusionStrategy(Protocol):
    def fuse(
        self,
        dense: Sequence[RetrievedCandidate],
        sparse: Sequence[RetrievedCandidate],
        *,
        limit: int,
    ) -> list[FusedCandidate]: ...


@dataclass(frozen=True, slots=True)
class ReciprocalRankFusion:
    """Rank-only fusion. Never mixes dense and sparse raw scores."""

    k: int = 60

    def fuse(
        self,
        dense: Sequence[RetrievedCandidate],
        sparse: Sequence[RetrievedCandidate],
        *,
        limit: int,
    ) -> list[FusedCandidate]:
        if self.k < 1:
            raise HybridFusionError("rrf k must be >= 1")
        if limit < 1:
            return []
        dense_best = _best_by_chunk(dense)
        sparse_best = _best_by_chunk(sparse)
        fused: list[FusedCandidate] = []
        for chunk_id in dense_best.keys() | sparse_best.keys():
            dense_hit = dense_best.get(chunk_id)
            sparse_hit = sparse_best.get(chunk_id)
            if dense_hit is not None and sparse_hit is not None:
                _assert_same_provenance(dense_hit, sparse_hit)
            primary = dense_hit if dense_hit is not None else sparse_hit
            if primary is None:
                raise HybridFusionError("fusion produced an empty candidate")
            score = 0.0
            if dense_hit is not None:
                score += 1.0 / (self.k + dense_hit.source_rank)
            if sparse_hit is not None:
                score += 1.0 / (self.k + sparse_hit.source_rank)
            fused.append(
                FusedCandidate(
                    chunk_id=primary.chunk_id,
                    rrf_score=score,
                    fused_rank=0,
                    collection_id=primary.collection_id,
                    document_id=primary.document_id,
                    document_version_id=primary.document_version_id,
                    page_start=primary.page_start,
                    page_end=primary.page_end,
                    text=primary.text,
                    dense_rank=dense_hit.source_rank if dense_hit is not None else None,
                    dense_score=dense_hit.source_score if dense_hit is not None else None,
                    sparse_rank=sparse_hit.source_rank if sparse_hit is not None else None,
                    sparse_score=sparse_hit.source_score if sparse_hit is not None else None,
                )
            )
        fused.sort(key=lambda item: (-item.rrf_score, str(item.chunk_id)))
        limited = fused[:limit]
        return [
            FusedCandidate(
                chunk_id=item.chunk_id,
                rrf_score=item.rrf_score,
                fused_rank=rank,
                collection_id=item.collection_id,
                document_id=item.document_id,
                document_version_id=item.document_version_id,
                page_start=item.page_start,
                page_end=item.page_end,
                text=item.text,
                dense_rank=item.dense_rank,
                dense_score=item.dense_score,
                sparse_rank=item.sparse_rank,
                sparse_score=item.sparse_score,
            )
            for rank, item in enumerate(limited, start=1)
        ]


def _best_by_chunk(candidates: Sequence[RetrievedCandidate]) -> dict[UUID, RetrievedCandidate]:
    best: dict[UUID, RetrievedCandidate] = {}
    for candidate in candidates:
        if candidate.source_rank < 1:
            raise HybridFusionError("invalid candidate rank")
        existing = best.get(candidate.chunk_id)
        if existing is None or candidate.source_rank < existing.source_rank:
            best[candidate.chunk_id] = candidate
    return best


def _assert_same_provenance(left: RetrievedCandidate, right: RetrievedCandidate) -> None:
    if (
        left.collection_id != right.collection_id
        or left.document_id != right.document_id
        or left.document_version_id != right.document_version_id
        or left.page_start != right.page_start
        or left.page_end != right.page_end
        or left.text != right.text
    ):
        raise HybridFusionError("duplicate chunk metadata conflict")
