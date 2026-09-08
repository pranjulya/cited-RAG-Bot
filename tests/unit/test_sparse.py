from __future__ import annotations

from uuid import uuid4

import pytest

from cited_rag.adapters.embedding.hashing import HashEmbeddingProvider
from cited_rag.adapters.retrieval.memory import MemoryRetrievalStore
from cited_rag.adapters.sparse import create_sparse_encoder
from cited_rag.adapters.sparse.lexical import LexicalSparseEncoder
from cited_rag.application.indexing import (
    assert_dense_and_sparse_complete,
    finalize_ready,
    persist_dense_index,
    persist_sparse_index,
)
from cited_rag.application.retrieval import retrieve_sparse
from cited_rag.config import Settings
from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.enums import DocumentVersionStatus, RetrievalSource
from cited_rag.domain.exceptions import PermanentIngestionError, SparseRetrievalError
from cited_rag.domain.indexing import IndexedPoint
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.document import DocumentVersion


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
        ingestion_status=DocumentVersionStatus.PROCESSING,
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
    version: DocumentVersion, chunks: list[Chunk], store: MemoryRetrievalStore
) -> None:
    config = EmbeddingConfig(dimension=8, batch_size=8, index_version="idx-1")
    await persist_dense_index(
        chunks,
        embedder=HashEmbeddingProvider(dimension=8),
        store=store,
        config=config,
    )
    await persist_sparse_index(
        chunks,
        encoder=LexicalSparseEncoder(),
        store=store,
        config=config,
    )


@pytest.mark.asyncio
async def test_lexical_encoder_is_deterministic() -> None:
    encoder = LexicalSparseEncoder()
    first = await encoder.encode_documents(["Policy-42 applies"])
    second = await encoder.encode_query("Policy-42 applies")
    assert first[0] == second
    assert first[0].indices


@pytest.mark.asyncio
async def test_sparse_upsert_keeps_dense_on_the_same_point() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "alpha")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    point = store.points[chunks[0].id]
    assert "dense" in point.vectors
    assert point.sparse is not None
    assert point.point_id == chunks[0].id


@pytest.mark.asyncio
async def test_sparse_cannot_be_written_before_dense() -> None:
    version = _version()
    chunk = _chunk(version, 0, "alpha")
    store = MemoryRetrievalStore()
    await store.ensure_collection(dense_dimension=8)
    with pytest.raises(PermanentIngestionError, match="before dense"):
        await persist_sparse_index(
            [chunk],
            encoder=LexicalSparseEncoder(),
            store=store,
            config=EmbeddingConfig(dimension=8),
        )


@pytest.mark.asyncio
async def test_identifier_query_ranks_the_matching_chunk() -> None:
    version = _version()
    chunks = [
        _chunk(version, 0, "general onboarding text"),
        _chunk(version, 1, "Form POLICY_42 must be signed"),
    ]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    hits = await retrieve_sparse(
        "POLICY_42",
        encoder=LexicalSparseEncoder(),
        store=store,
        chunks=chunks,
        collection_id=version.collection_id,
        document_version_ids=[version.id],
        top_k=5,
    )
    assert hits
    assert hits[0].chunk_id == chunks[1].id
    assert hits[0].source is RetrievalSource.SPARSE
    assert "POLICY_42" in hits[0].text


@pytest.mark.asyncio
async def test_sparse_search_is_collection_scoped() -> None:
    version = _version()
    other = _version()
    chunks = [_chunk(version, 0, "secret token ZX-99")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    hits = await retrieve_sparse(
        "ZX-99",
        encoder=LexicalSparseEncoder(),
        store=store,
        chunks=chunks,
        collection_id=other.collection_id,
        document_version_ids=[version.id],
        top_k=5,
    )
    assert hits == []


@pytest.mark.asyncio
async def test_empty_version_filter_returns_no_hits() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "needle")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    hits = await retrieve_sparse(
        "needle",
        encoder=LexicalSparseEncoder(),
        store=store,
        chunks=chunks,
        collection_id=version.collection_id,
        document_version_ids=[],
        top_k=5,
    )
    assert hits == []


@pytest.mark.asyncio
async def test_missing_authoritative_chunk_is_sparse_retrieval_error() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "Form POLICY_42 must be signed")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    with pytest.raises(SparseRetrievalError, match="authoritative"):
        await retrieve_sparse(
            "POLICY_42",
            encoder=LexicalSparseEncoder(),
            store=store,
            chunks=[],
            collection_id=version.collection_id,
            document_version_ids=[version.id],
            top_k=5,
        )


@pytest.mark.asyncio
async def test_malformed_hit_payload_is_sparse_retrieval_error() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "Form POLICY_42 must be signed")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    point = store.points[chunks[0].id]
    incomplete = dict(point.payload)
    incomplete.pop("page_start")
    store.points[chunks[0].id] = IndexedPoint(
        point_id=point.point_id,
        vectors=point.vectors,
        payload=incomplete,
        sparse=point.sparse,
    )
    with pytest.raises(SparseRetrievalError, match="malformed"):
        await retrieve_sparse(
            "POLICY_42",
            encoder=LexicalSparseEncoder(),
            store=store,
            chunks=chunks,
            collection_id=version.collection_id,
            document_version_ids=[version.id],
            top_k=5,
        )


@pytest.mark.asyncio
async def test_store_failure_is_sparse_retrieval_error() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "Form POLICY_42 must be signed")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    store.fail_search = True
    with pytest.raises(SparseRetrievalError, match="unavailable"):
        await retrieve_sparse(
            "POLICY_42",
            encoder=LexicalSparseEncoder(),
            store=store,
            chunks=chunks,
            collection_id=version.collection_id,
            document_version_ids=[version.id],
            top_k=5,
        )


@pytest.mark.asyncio
async def test_incomplete_index_blocks_ready() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "only dense")]
    store = MemoryRetrievalStore()
    await persist_dense_index(
        chunks,
        embedder=HashEmbeddingProvider(dimension=8),
        store=store,
        config=EmbeddingConfig(dimension=8),
    )
    with pytest.raises(PermanentIngestionError, match="incomplete"):
        await assert_dense_and_sparse_complete(store, chunks, index_version="v1")


@pytest.mark.asyncio
async def test_payload_mismatch_blocks_ready() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "ready text")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    point = store.points[chunks[0].id]
    store.points[chunks[0].id] = IndexedPoint(
        point_id=point.point_id,
        vectors=point.vectors,
        payload={**point.payload, "collection_id": str(uuid4())},
        sparse=point.sparse,
    )
    with pytest.raises(PermanentIngestionError, match="payload"):
        await assert_dense_and_sparse_complete(store, chunks, index_version="idx-1")


def test_factory_derives_bm42_identity_from_backend_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[object] = []

    class _FakeBm42:
        def __init__(self, config: object) -> None:
            captured.append(config)
            self.config = config

    monkeypatch.setattr(
        "cited_rag.adapters.sparse.fastembed_bm42.FastEmbedBm42Encoder",
        _FakeBm42,
    )
    settings = Settings(
        _env_file=None,
        sparse_encoder_backend="bm42",
        sparse_encoder_name="lexical_tf_v1",
        sparse_encoder_version="v1",
    )
    encoder = create_sparse_encoder(settings)
    assert settings.sparse_encoder_name == "fastembed-bm42"
    assert settings.sparse_encoder_version == "Qdrant/bm42-all-minilm-l6-v2-attentions"
    assert encoder.config.name == "fastembed-bm42"
    assert encoder.config.version == "Qdrant/bm42-all-minilm-l6-v2-attentions"
    assert captured[0] == encoder.config


@pytest.mark.asyncio
async def test_missing_payload_field_blocks_ready() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "ready text")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    point = store.points[chunks[0].id]
    incomplete = dict(point.payload)
    incomplete.pop("collection_id")
    store.points[chunks[0].id] = IndexedPoint(
        point_id=point.point_id,
        vectors=point.vectors,
        payload=incomplete,
        sparse=point.sparse,
    )
    with pytest.raises(PermanentIngestionError, match="payload"):
        await assert_dense_and_sparse_complete(store, chunks, index_version="idx-1")


class _Versions:
    def __init__(self) -> None:
        self.ready: DocumentVersion | None = None
        self.saved: dict[str, str] | None = None

    async def set_sparse_encoder_config(self, _version_id: object, config: dict[str, str]) -> None:
        self.saved = config

    async def transition(self, version_id: object, _from: object, _to: object) -> DocumentVersion:
        assert self.saved is not None
        self.ready = _version()
        object.__setattr__(self.ready, "id", version_id)
        object.__setattr__(self.ready, "ingestion_status", DocumentVersionStatus.READY)
        return self.ready


class _Documents:
    def __init__(self) -> None:
        self.active: object | None = None

    async def set_active_version(self, document_id: object, version_id: object) -> None:
        self.active = (document_id, version_id)


class _Uow:
    def __init__(self, versions: _Versions, documents: _Documents) -> None:
        self.versions = versions
        self.documents = documents


@pytest.mark.asyncio
async def test_finalize_sets_ready_after_dense_and_sparse() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "ready text")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    versions = _Versions()
    documents = _Documents()
    ready = await finalize_ready(
        _Uow(versions, documents),  # type: ignore[arg-type]
        version,
        chunks,
        store=store,
        encoder_config=LexicalSparseEncoder().config,
        index_version="idx-1",
    )
    assert ready.ingestion_status is DocumentVersionStatus.READY
    assert documents.active == (version.document_id, version.id)
    assert versions.saved == {"name": "lexical_tf_v1", "version": "v1"}
