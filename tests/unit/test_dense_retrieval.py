from __future__ import annotations

from uuid import uuid4

import pytest

from cited_rag.adapters.retrieval.memory import MemoryRetrievalStore
from cited_rag.application.indexing import persist_dense_index
from cited_rag.application.retrieval import retrieve_dense
from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.enums import RetrievalSource
from cited_rag.domain.exceptions import DenseRetrievalError
from cited_rag.domain.indexing import IndexedPoint
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.document import DocumentVersion


class _AliasEmbedder:
    """Maps paraphrases to the same vector so dense search can be tested without a model."""

    def __init__(self) -> None:
        self.dimension = 4
        self.table = {
            "the cat sat": [1.0, 0.0, 0.0, 0.0],
            "a feline sat": [1.0, 0.0, 0.0, 0.0],
            "budget table 2024": [0.0, 1.0, 0.0, 0.0],
        }

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def _vector(self, text: str) -> list[float]:
        return list(self.table.get(text, [0.0, 0.0, 1.0, 0.0]))


class _TimeoutEmbedder(_AliasEmbedder):
    async def embed_query(self, text: str) -> list[float]:
        raise TimeoutError("embedding timed out")


def _version() -> DocumentVersion:
    return DocumentVersion(
        document_id=uuid4(),
        collection_id=uuid4(),
        version_number=1,
        content_hash="h",
        original_filename="a.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        storage_uri="local://a.pdf",
    )


def _chunk(version: DocumentVersion, order: int, text: str) -> Chunk:
    return Chunk(
        collection_id=version.collection_id,
        document_id=version.document_id,
        document_version_id=version.id,
        page_start=1,
        page_end=1,
        chunk_order=order,
        text=text,
        content_hash=f"h{order}",
    )


async def _index(
    version: DocumentVersion,
    chunks: list[Chunk],
    store: MemoryRetrievalStore,
    embedder: _AliasEmbedder,
) -> None:
    await persist_dense_index(
        chunks,
        embedder=embedder,
        store=store,
        config=EmbeddingConfig(dimension=embedder.dimension, batch_size=8),
    )


@pytest.mark.asyncio
async def test_paraphrase_query_returns_matching_chunk() -> None:
    version = _version()
    chunks = [
        _chunk(version, 0, "the cat sat"),
        _chunk(version, 1, "budget table 2024"),
    ]
    store = MemoryRetrievalStore()
    embedder = _AliasEmbedder()
    await _index(version, chunks, store, embedder)
    hits = await retrieve_dense(
        "a feline sat",
        embedder=embedder,
        store=store,
        chunks=chunks,
        collection_id=version.collection_id,
        document_version_ids=[version.id],
        top_k=5,
    )
    assert hits
    assert hits[0].chunk_id == chunks[0].id
    assert hits[0].source is RetrievalSource.DENSE
    assert hits[0].source_rank == 1


@pytest.mark.asyncio
async def test_dense_search_is_collection_scoped() -> None:
    version = _version()
    other = _version()
    chunks = [_chunk(version, 0, "the cat sat")]
    store = MemoryRetrievalStore()
    embedder = _AliasEmbedder()
    await _index(version, chunks, store, embedder)
    hits = await retrieve_dense(
        "a feline sat",
        embedder=embedder,
        store=store,
        chunks=chunks,
        collection_id=other.collection_id,
        document_version_ids=[version.id],
        top_k=5,
    )
    assert hits == []


@pytest.mark.asyncio
async def test_empty_ready_set_returns_no_hits() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "the cat sat")]
    store = MemoryRetrievalStore()
    embedder = _AliasEmbedder()
    await _index(version, chunks, store, embedder)
    hits = await retrieve_dense(
        "a feline sat",
        embedder=embedder,
        store=store,
        chunks=chunks,
        collection_id=version.collection_id,
        document_version_ids=[],
        top_k=5,
    )
    assert hits == []


@pytest.mark.asyncio
async def test_top_k_truncates_candidates() -> None:
    version = _version()
    chunks = [
        _chunk(version, 0, "the cat sat"),
        _chunk(version, 1, "a feline sat"),
        _chunk(version, 2, "budget table 2024"),
    ]
    store = MemoryRetrievalStore()
    embedder = _AliasEmbedder()
    await _index(version, chunks, store, embedder)
    hits = await retrieve_dense(
        "a feline sat",
        embedder=embedder,
        store=store,
        chunks=chunks,
        collection_id=version.collection_id,
        document_version_ids=[version.id],
        top_k=1,
    )
    assert len(hits) == 1
    assert hits[0].chunk_id in {chunks[0].id, chunks[1].id}


@pytest.mark.asyncio
async def test_embedding_timeout_is_dense_retrieval_error() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "the cat sat")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store, _AliasEmbedder())
    with pytest.raises(DenseRetrievalError, match="timed out"):
        await retrieve_dense(
            "a feline sat",
            embedder=_TimeoutEmbedder(),
            store=store,
            chunks=chunks,
            collection_id=version.collection_id,
            document_version_ids=[version.id],
            top_k=5,
        )


@pytest.mark.asyncio
async def test_missing_authoritative_chunk_is_dense_retrieval_error() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "the cat sat")]
    store = MemoryRetrievalStore()
    embedder = _AliasEmbedder()
    await _index(version, chunks, store, embedder)
    with pytest.raises(DenseRetrievalError, match="authoritative"):
        await retrieve_dense(
            "a feline sat",
            embedder=embedder,
            store=store,
            chunks=[],
            collection_id=version.collection_id,
            document_version_ids=[version.id],
            top_k=5,
        )


@pytest.mark.asyncio
async def test_stale_hit_payload_is_dense_retrieval_error() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "the cat sat")]
    store = MemoryRetrievalStore()
    embedder = _AliasEmbedder()
    await _index(version, chunks, store, embedder)
    point = store.points[chunks[0].id]
    store.points[chunks[0].id] = IndexedPoint(
        point_id=point.point_id,
        vectors=point.vectors,
        payload={**point.payload, "document_id": str(uuid4())},
        sparse=point.sparse,
    )
    with pytest.raises(DenseRetrievalError, match="authoritative"):
        await retrieve_dense(
            "a feline sat",
            embedder=embedder,
            store=store,
            chunks=chunks,
            collection_id=version.collection_id,
            document_version_ids=[version.id],
            top_k=5,
        )


@pytest.mark.asyncio
async def test_malformed_hit_payload_is_dense_retrieval_error() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "the cat sat")]
    store = MemoryRetrievalStore()
    embedder = _AliasEmbedder()
    await _index(version, chunks, store, embedder)
    point = store.points[chunks[0].id]
    incomplete = dict(point.payload)
    incomplete.pop("page_start")
    store.points[chunks[0].id] = IndexedPoint(
        point_id=point.point_id,
        vectors=point.vectors,
        payload=incomplete,
        sparse=point.sparse,
    )
    with pytest.raises(DenseRetrievalError, match="malformed"):
        await retrieve_dense(
            "a feline sat",
            embedder=embedder,
            store=store,
            chunks=chunks,
            collection_id=version.collection_id,
            document_version_ids=[version.id],
            top_k=5,
        )


@pytest.mark.asyncio
async def test_store_failure_is_dense_retrieval_error() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "the cat sat")]
    store = MemoryRetrievalStore()
    embedder = _AliasEmbedder()
    await _index(version, chunks, store, embedder)
    store.fail_search = True
    with pytest.raises(DenseRetrievalError, match="unavailable"):
        await retrieve_dense(
            "a feline sat",
            embedder=embedder,
            store=store,
            chunks=chunks,
            collection_id=version.collection_id,
            document_version_ids=[version.id],
            top_k=5,
        )
