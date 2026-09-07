from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from cited_rag.domain.exceptions import TransientIngestionError
from cited_rag.domain.indexing import (
    DENSE_VECTOR_NAME,
    NAMED_VECTORS,
    SPARSE_VECTOR_NAME,
    IndexedPoint,
)


class MemoryRetrievalStore:
    """In-process named-vector store for unit tests. Not used in production."""

    def __init__(self) -> None:
        self.points: dict[UUID, IndexedPoint] = {}
        self.vector_names: set[str] = set()
        self.dense_dimension: int | None = None
        self.fail_upsert = False

    async def ensure_collection(self, *, dense_dimension: int) -> None:
        self.dense_dimension = dense_dimension
        self.vector_names = set(NAMED_VECTORS)

    async def upsert_dense(self, points: Sequence[IndexedPoint]) -> None:
        if self.fail_upsert:
            raise TransientIngestionError("retrieval store unavailable")
        for point in points:
            if DENSE_VECTOR_NAME not in point.vectors:
                raise TransientIngestionError("dense vector missing")
            if SPARSE_VECTOR_NAME in point.vectors:
                raise TransientIngestionError("sparse vectors are owned by a later phase")
            self.points[point.point_id] = point

    async def get_point(self, point_id: UUID) -> IndexedPoint | None:
        return self.points.get(point_id)
