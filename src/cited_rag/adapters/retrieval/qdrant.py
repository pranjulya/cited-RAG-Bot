from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    PointVectors,
    SparseVectorParams,
    VectorParams,
)
from qdrant_client.models import (
    SparseVector as QdrantSparseVector,
)

from cited_rag.domain.exceptions import PermanentIngestionError, TransientIngestionError
from cited_rag.domain.indexing import (
    DENSE_VECTOR_NAME,
    NAMED_VECTORS,
    PAYLOAD_FIELDS,
    SPARSE_VECTOR_NAME,
    IndexedPoint,
    SearchHit,
    SparseVector,
)

_KEYWORD_PAYLOAD = {
    "collection_id",
    "document_id",
    "document_version_id",
    "index_version",
}


def dense_and_sparse_params(
    dimension: int,
) -> tuple[dict[str, VectorParams], dict[str, SparseVectorParams]]:
    return (
        {DENSE_VECTOR_NAME: VectorParams(size=dimension, distance=Distance.COSINE)},
        {SPARSE_VECTOR_NAME: SparseVectorParams()},
    )


class QdrantRetrievalStore:
    """One application collection with named vectors dense and sparse."""

    def __init__(self, *, url: str, collection_name: str) -> None:
        self._client = AsyncQdrantClient(url=url)
        self.collection_name = collection_name
        self.vector_names: set[str] = set()

    async def close(self) -> None:
        closer = getattr(self._client, "close", None)
        if closer is not None:
            await closer()

    async def ensure_collection(self, *, dense_dimension: int) -> None:
        try:
            exists = await self._client.collection_exists(self.collection_name)
            if exists:
                await self._reject_dense_only()
            else:
                dense, sparse = dense_and_sparse_params(dense_dimension)
                await self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=dense,
                    sparse_vectors_config=sparse,
                )
                for field in PAYLOAD_FIELDS:
                    schema = (
                        PayloadSchemaType.KEYWORD
                        if field in _KEYWORD_PAYLOAD
                        else PayloadSchemaType.INTEGER
                    )
                    await self._client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field,
                        field_schema=schema,
                    )
            self.vector_names = set(NAMED_VECTORS)
        except PermanentIngestionError:
            raise
        except UnexpectedResponse as exc:
            raise TransientIngestionError("retrieval store unavailable") from exc
        except Exception as exc:
            raise TransientIngestionError("retrieval store unavailable") from exc

    async def upsert_dense(self, points: Sequence[IndexedPoint]) -> None:
        if not points:
            return
        structs = [
            PointStruct(
                id=str(point.point_id),
                vector={DENSE_VECTOR_NAME: point.vectors[DENSE_VECTOR_NAME]},
                payload=dict(point.payload),
            )
            for point in points
        ]
        try:
            await self._client.upsert(collection_name=self.collection_name, points=structs)
        except UnexpectedResponse as exc:
            raise TransientIngestionError("retrieval store unavailable") from exc
        except Exception as exc:
            raise TransientIngestionError("retrieval store unavailable") from exc

    async def get_point(self, point_id: UUID) -> IndexedPoint | None:
        try:
            records = await self._client.retrieve(
                collection_name=self.collection_name,
                ids=[str(point_id)],
                with_vectors=True,
            )
        except UnexpectedResponse as exc:
            raise TransientIngestionError("retrieval store unavailable") from exc
        except Exception as exc:
            raise TransientIngestionError("retrieval store unavailable") from exc
        if not records:
            return None
        record = records[0]
        vectors = _named_dense(record.vector)
        payload = {key: record.payload[key] for key in PAYLOAD_FIELDS if record.payload}
        return IndexedPoint(
            point_id=point_id,
            vectors=vectors,
            payload=payload,
            sparse=_named_sparse(record.vector),
        )

    async def upsert_sparse(self, points: Sequence[IndexedPoint]) -> None:
        if not points:
            return
        structs = []
        for point in points:
            if point.sparse is None:
                raise PermanentIngestionError(
                    "sparse vector missing",
                    failure_code="SPARSE_INDEX_FAILED",
                )
            structs.append(
                PointVectors(
                    id=str(point.point_id),
                    vector={
                        SPARSE_VECTOR_NAME: QdrantSparseVector(
                            indices=list(point.sparse.indices),
                            values=list(point.sparse.values),
                        )
                    },
                )
            )
        try:
            await self._client.update_vectors(
                collection_name=self.collection_name,
                points=structs,
            )
        except UnexpectedResponse as exc:
            raise TransientIngestionError("retrieval store unavailable") from exc
        except Exception as exc:
            raise TransientIngestionError("retrieval store unavailable") from exc

    async def search_sparse(
        self,
        vector: SparseVector,
        *,
        collection_id: UUID,
        document_version_ids: Sequence[UUID],
        top_k: int,
    ) -> list[SearchHit]:
        if not document_version_ids or top_k < 1:
            return []
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="collection_id",
                    match=MatchValue(value=str(collection_id)),
                ),
                FieldCondition(
                    key="document_version_id",
                    match=MatchAny(any=[str(version_id) for version_id in document_version_ids]),
                ),
            ]
        )
        try:
            result = await self._client.query_points(
                collection_name=self.collection_name,
                query=QdrantSparseVector(indices=list(vector.indices), values=list(vector.values)),
                using=SPARSE_VECTOR_NAME,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
        except UnexpectedResponse as exc:
            raise TransientIngestionError("retrieval store unavailable") from exc
        except Exception as exc:
            raise TransientIngestionError("retrieval store unavailable") from exc
        return _hits_from_query(result)

    async def scroll_collection(
        self, *, collection_id: UUID, limit: int = 10
    ) -> list[IndexedPoint]:
        """Dummy filtered read for index tests. Product dense retrieval is Phase 08."""
        try:
            points, _offset = await self._client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="collection_id",
                            match=MatchValue(value=str(collection_id)),
                        )
                    ]
                ),
                limit=limit,
                with_vectors=True,
                with_payload=True,
            )
        except UnexpectedResponse as exc:
            raise TransientIngestionError("retrieval store unavailable") from exc
        except Exception as exc:
            raise TransientIngestionError("retrieval store unavailable") from exc
        found: list[IndexedPoint] = []
        for record in points:
            found.append(
                IndexedPoint(
                    point_id=UUID(str(record.id)),
                    vectors=_named_dense(record.vector),
                    payload={key: record.payload[key] for key in PAYLOAD_FIELDS if record.payload},
                    sparse=_named_sparse(record.vector),
                )
            )
        return found

    async def _reject_dense_only(self) -> None:
        info = await self._client.get_collection(self.collection_name)
        params = info.config.params
        dense = getattr(params, "vectors", None)
        sparse = getattr(params, "sparse_vectors", None)
        dense_names = set(dense.keys()) if isinstance(dense, dict) else set()
        sparse_names = set(sparse.keys()) if isinstance(sparse, dict) else set()
        if DENSE_VECTOR_NAME not in dense_names or SPARSE_VECTOR_NAME not in sparse_names:
            raise PermanentIngestionError(
                "dense-only qdrant collection is not allowed",
                failure_code="INDEX_UNAVAILABLE",
            )


def _hits_from_query(result: Any) -> list[SearchHit]:
    points = getattr(result, "points", result)
    hits: list[SearchHit] = []
    for record in points:
        payload = getattr(record, "payload", None) or {}
        hits.append(
            SearchHit(
                point_id=UUID(str(record.id)),
                score=float(record.score),
                payload={key: payload[key] for key in PAYLOAD_FIELDS if key in payload},
            )
        )
    return hits


def _named_sparse(vector: Any) -> SparseVector | None:
    if not isinstance(vector, dict) or SPARSE_VECTOR_NAME not in vector:
        return None
    raw = vector[SPARSE_VECTOR_NAME]
    if raw is None:
        return None
    indices = getattr(raw, "indices", None)
    values = getattr(raw, "values", None)
    if indices is None and isinstance(raw, dict):
        indices = raw.get("indices")
        values = raw.get("values")
    if indices is None or values is None:
        return None
    index_list = [int(index) for index in list(indices)]
    value_list = [float(value) for value in list(values)]
    if not index_list:
        return None
    return SparseVector(indices=index_list, values=value_list)


def _named_dense(vector: Any) -> dict[str, list[float]]:
    if isinstance(vector, dict) and DENSE_VECTOR_NAME in vector:
        values = vector[DENSE_VECTOR_NAME]
        if hasattr(values, "data"):
            values = values.data
        return {DENSE_VECTOR_NAME: list(values)}
    if isinstance(vector, list):
        return {DENSE_VECTOR_NAME: list(vector)}
    return {}
