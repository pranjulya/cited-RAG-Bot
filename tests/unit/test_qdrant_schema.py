from __future__ import annotations

from types import SimpleNamespace

import pytest
from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

from cited_rag.adapters.retrieval.qdrant import (
    _record_payload,
    assert_existing_collection_schema,
    missing_payload_index_fields,
)
from cited_rag.domain.exceptions import PermanentIngestionError
from cited_rag.domain.indexing import PAYLOAD_FIELDS


def _info(
    *,
    size: int = 32,
    distance: object = Distance.COSINE,
    payload: dict[str, object] | None = None,
) -> object:
    return SimpleNamespace(
        config=SimpleNamespace(
            params=SimpleNamespace(
                vectors={"dense": VectorParams(size=size, distance=distance)},  # type: ignore[arg-type]
                sparse_vectors={"sparse": object()},
            )
        ),
        payload_schema=payload if payload is not None else {},
    )


def test_existing_collection_rejects_wrong_dense_dimension() -> None:
    with pytest.raises(PermanentIngestionError, match="dimension"):
        assert_existing_collection_schema(_info(size=8), dense_dimension=32)


def test_existing_collection_rejects_non_cosine_distance() -> None:
    with pytest.raises(PermanentIngestionError, match="cosine"):
        assert_existing_collection_schema(_info(distance=Distance.EUCLID), dense_dimension=32)


def test_existing_collection_rejects_dense_only() -> None:
    info = SimpleNamespace(
        config=SimpleNamespace(
            params=SimpleNamespace(vectors={"dense": object()}, sparse_vectors={})
        ),
        payload_schema={},
    )
    with pytest.raises(PermanentIngestionError, match="dense-only"):
        assert_existing_collection_schema(info, dense_dimension=32)


def test_missing_payload_indexes_are_listed() -> None:
    info = _info(payload={"collection_id": object()})
    missing = missing_payload_index_fields(info)
    assert missing == [field for field in PAYLOAD_FIELDS if field != "collection_id"]


def test_record_payload_omits_missing_fields() -> None:
    record = SimpleNamespace(payload={"collection_id": "abc", "page_start": 1})
    assert _record_payload(record) == {"collection_id": "abc", "page_start": 1}


def test_record_payload_empty_when_payload_missing() -> None:
    assert _record_payload(SimpleNamespace(payload=None)) == {}
    assert _record_payload(SimpleNamespace()) == {}


def test_wrong_payload_index_type_is_rejected() -> None:
    info = _info(
        payload={
            field: SimpleNamespace(data_type=PayloadSchemaType.KEYWORD) for field in PAYLOAD_FIELDS
        }
    )
    with pytest.raises(PermanentIngestionError, match="payload index"):
        assert_existing_collection_schema(info, dense_dimension=32)
