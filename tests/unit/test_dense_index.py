from __future__ import annotations

from uuid import uuid4

import pytest

from cited_rag.adapters.embedding.hashing import HashEmbeddingProvider
from cited_rag.adapters.retrieval.memory import MemoryRetrievalStore
from cited_rag.adapters.retrieval.qdrant import dense_and_sparse_params
from cited_rag.application.indexing import persist_dense_index
from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.exceptions import PermanentIngestionError, TransientIngestionError
from cited_rag.domain.indexing import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.document import DocumentVersion


def test_qdrant_collection_params_include_dense_and_sparse() -> None:
    dense, sparse = dense_and_sparse_params(32)
    assert set(dense) == {DENSE_VECTOR_NAME}
    assert set(sparse) == {SPARSE_VECTOR_NAME}
    assert dense[DENSE_VECTOR_NAME].size == 32


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


class _SizedEmbedder:
    def __init__(self, dimension: int) -> None:
        self.dimension = dimension
        self.batch_sizes: list[int] = []

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.batch_sizes.append(len(texts))
        return [[0.0] * self.dimension for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [0.0] * self.dimension


class _TimeoutEmbedder:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise TimeoutError("embedding timed out")

    async def embed_query(self, text: str) -> list[float]:
        raise TimeoutError("embedding timed out")


class _MismatchEmbedder:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0, 1.0] for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [0.0, 1.0]


@pytest.mark.asyncio
async def test_dense_upsert_uses_chunk_uuid_and_provenance_payload() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "first"), _chunk(version, 1, "second")]
    store = MemoryRetrievalStore()
    config = EmbeddingConfig(dimension=8, batch_size=16, index_version="idx-1")
    records = await persist_dense_index(
        chunks,
        embedder=HashEmbeddingProvider(dimension=8),
        store=store,
        config=config,
    )
    assert store.vector_names == {"dense", "sparse"}
    assert [record.point_id for record in records] == [chunks[0].id, chunks[1].id]
    first = store.points[chunks[0].id]
    assert first.payload["collection_id"] == str(version.collection_id)
    assert first.payload["document_id"] == str(version.document_id)
    assert first.payload["document_version_id"] == str(version.id)
    assert first.payload["page_start"] == 1
    assert first.payload["page_end"] == 1
    assert first.payload["chunk_order"] == 0
    assert first.payload["index_version"] == "idx-1"
    assert "text" not in first.payload
    assert "sparse" not in first.vectors
    assert "dense" in first.vectors


@pytest.mark.asyncio
async def test_dense_upsert_is_idempotent_for_the_same_chunk_ids() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "same")]
    store = MemoryRetrievalStore()
    config = EmbeddingConfig(dimension=8, index_version="idx-1")
    embedder = HashEmbeddingProvider(dimension=8)
    first = await persist_dense_index(chunks, embedder=embedder, store=store, config=config)
    second = await persist_dense_index(chunks, embedder=embedder, store=store, config=config)
    assert list(store.points) == [chunks[0].id]
    assert first[0].vectors["dense"] == second[0].vectors["dense"]


@pytest.mark.asyncio
async def test_dense_index_batches_embedding_calls() -> None:
    version = _version()
    chunks = [_chunk(version, index, f"t{index}") for index in range(5)]
    embedder = _SizedEmbedder(dimension=4)
    store = MemoryRetrievalStore()
    await persist_dense_index(
        chunks,
        embedder=embedder,
        store=store,
        config=EmbeddingConfig(dimension=4, batch_size=2),
    )
    assert embedder.batch_sizes == [2, 2, 1]


@pytest.mark.asyncio
async def test_dimension_mismatch_is_permanent() -> None:
    version = _version()
    store = MemoryRetrievalStore()
    with pytest.raises(PermanentIngestionError, match="dimension"):
        await persist_dense_index(
            [_chunk(version, 0, "x")],
            embedder=_MismatchEmbedder(),
            store=store,
            config=EmbeddingConfig(dimension=8),
        )
    assert store.points == {}


@pytest.mark.asyncio
async def test_embedding_timeout_is_transient() -> None:
    version = _version()
    with pytest.raises(TransientIngestionError, match="timed out"):
        await persist_dense_index(
            [_chunk(version, 0, "x")],
            embedder=_TimeoutEmbedder(),
            store=MemoryRetrievalStore(),
            config=EmbeddingConfig(dimension=8),
        )
