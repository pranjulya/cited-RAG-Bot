from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SparseVector:
    indices: list[int]
    values: list[float]

    def __post_init__(self) -> None:
        if len(self.indices) != len(self.values):
            raise ValueError("sparse indices and values must be the same length")


DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"
NAMED_VECTORS = frozenset({DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME})
PAYLOAD_FIELDS = (
    "collection_id",
    "document_id",
    "document_version_id",
    "page_start",
    "page_end",
    "chunk_order",
    "index_version",
)


@dataclass(frozen=True, slots=True)
class IndexedPoint:
    point_id: UUID
    vectors: dict[str, list[float]]
    payload: dict[str, str | int]
    sparse: SparseVector | None = None


@dataclass(frozen=True, slots=True)
class SearchHit:
    point_id: UUID
    score: float
    payload: dict[str, str | int]
