from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from cited_rag.domain.indexing import IndexedPoint


class RetrievalStore(Protocol):
    vector_names: set[str]

    async def ensure_collection(self, *, dense_dimension: int) -> None: ...

    async def upsert_dense(self, points: Sequence[IndexedPoint]) -> None: ...

    async def get_point(self, point_id: UUID) -> IndexedPoint | None: ...
