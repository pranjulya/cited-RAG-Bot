from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from cited_rag.domain.exceptions import PermanentIngestionError, TransientIngestionError
from cited_rag.domain.indexing import (
    DENSE_VECTOR_NAME,
    NAMED_VECTORS,
    SPARSE_VECTOR_NAME,
    IndexedPoint,
    SearchHit,
    SparseVector,
)


class MemoryRetrievalStore:
    """In-process named-vector store for unit tests. Not used in production."""

    def __init__(self) -> None:
        self.points: dict[UUID, IndexedPoint] = {}
        self.vector_names: set[str] = set()
        self.dense_dimension: int | None = None
        self.fail_upsert = False
        self.fail_search = False

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
                raise TransientIngestionError("upsert dense with named sparse is not allowed")
            self.points[point.point_id] = point

    async def upsert_sparse(self, points: Sequence[IndexedPoint]) -> None:
        if self.fail_upsert:
            raise TransientIngestionError("retrieval store unavailable")
        for point in points:
            if point.sparse is None or not point.sparse.indices:
                raise PermanentIngestionError(
                    "sparse vector missing",
                    failure_code="SPARSE_INDEX_FAILED",
                )
            existing = self.points.get(point.point_id)
            if existing is None or DENSE_VECTOR_NAME not in existing.vectors:
                raise PermanentIngestionError(
                    "cannot upsert sparse before dense",
                    failure_code="INDEX_INCOMPLETE",
                )
            self.points[point.point_id] = IndexedPoint(
                point_id=existing.point_id,
                vectors=existing.vectors,
                payload=existing.payload,
                sparse=point.sparse,
            )

    async def get_point(self, point_id: UUID) -> IndexedPoint | None:
        return self.points.get(point_id)

    async def search_dense(
        self,
        vector: Sequence[float],
        *,
        collection_id: UUID,
        document_version_ids: Sequence[UUID],
        top_k: int,
    ) -> list[SearchHit]:
        if self.fail_search:
            raise TransientIngestionError("retrieval store unavailable")
        allowed = {str(version_id) for version_id in document_version_ids}
        if not allowed or top_k < 1:
            return []
        scored: list[SearchHit] = []
        for point in self.points.values():
            if not _payload_matches(point, collection_id, allowed):
                continue
            dense = point.vectors.get(DENSE_VECTOR_NAME)
            if not dense:
                continue
            score = _cosine(vector, dense)
            scored.append(SearchHit(point_id=point.point_id, score=score, payload=point.payload))
        scored.sort(key=lambda hit: hit.score, reverse=True)
        return scored[:top_k]

    async def search_sparse(
        self,
        vector: SparseVector,
        *,
        collection_id: UUID,
        document_version_ids: Sequence[UUID],
        top_k: int,
    ) -> list[SearchHit]:
        if self.fail_search:
            raise TransientIngestionError("retrieval store unavailable")
        allowed = {str(version_id) for version_id in document_version_ids}
        if not allowed or top_k < 1:
            return []
        scored: list[SearchHit] = []
        for point in self.points.values():
            if not _payload_matches(point, collection_id, allowed):
                continue
            if point.sparse is None:
                continue
            score = _sparse_dot(vector, point.sparse)
            if score <= 0:
                continue
            scored.append(SearchHit(point_id=point.point_id, score=score, payload=point.payload))
        scored.sort(key=lambda hit: hit.score, reverse=True)
        return scored[:top_k]


def _payload_matches(point: IndexedPoint, collection_id: UUID, allowed_versions: set[str]) -> bool:
    return (
        point.payload.get("collection_id") == str(collection_id)
        and point.payload.get("document_version_id") in allowed_versions
    )


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    return float(sum(a * b for a, b in zip(left, right, strict=True)))


def _sparse_dot(left: SparseVector, right: SparseVector) -> float:
    right_map = dict(zip(right.indices, right.values, strict=True))
    return sum(
        value * right_map.get(index, 0.0)
        for index, value in zip(left.indices, left.values, strict=True)
    )
