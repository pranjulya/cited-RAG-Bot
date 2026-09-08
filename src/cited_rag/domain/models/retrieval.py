from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from cited_rag.domain.enums import RetrievalSource


@dataclass(frozen=True, slots=True)
class RetrievedCandidate:
    chunk_id: UUID
    source: RetrievalSource
    source_rank: int
    source_score: float
    collection_id: UUID
    document_id: UUID
    document_version_id: UUID
    page_start: int
    page_end: int
    text: str


@dataclass(frozen=True, slots=True)
class FusedCandidate:
    chunk_id: UUID
    rrf_score: float
    fused_rank: int
    collection_id: UUID
    document_id: UUID
    document_version_id: UUID
    page_start: int
    page_end: int
    text: str
    dense_rank: int | None
    dense_score: float | None
    sparse_rank: int | None
    sparse_score: float | None
