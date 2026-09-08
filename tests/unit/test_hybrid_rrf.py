from __future__ import annotations

from uuid import uuid4

import pytest

from cited_rag.adapters.embedding.hashing import HashEmbeddingProvider
from cited_rag.adapters.retrieval.memory import MemoryRetrievalStore
from cited_rag.adapters.sparse.lexical import LexicalSparseEncoder
from cited_rag.application.indexing import persist_dense_index, persist_sparse_index
from cited_rag.application.retrieval import ReciprocalRankFusion, retrieve_hybrid
from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.enums import RetrievalSource
from cited_rag.domain.exceptions import DenseRetrievalError, HybridFusionError, SparseRetrievalError
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.document import DocumentVersion
from cited_rag.domain.models.evaluation import EvaluationRunConfig
from cited_rag.domain.models.retrieval import RetrievedCandidate


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


def _hit(
    chunk: Chunk,
    *,
    source: RetrievalSource,
    rank: int,
    score: float = 1.0,
) -> RetrievedCandidate:
    return RetrievedCandidate(
        chunk_id=chunk.id,
        source=source,
        source_rank=rank,
        source_score=score,
        collection_id=chunk.collection_id,
        document_id=chunk.document_id,
        document_version_id=chunk.document_version_id,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        text=chunk.text,
    )


class _TimeoutEmbedder(HashEmbeddingProvider):
    async def embed_query(self, text: str) -> list[float]:
        raise TimeoutError("embedding timed out")


class _TimeoutEncoder(LexicalSparseEncoder):
    async def encode_query(self, text: str):  # type: ignore[override]
        raise TimeoutError("sparse encoding timed out")


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


def test_rrf_prefers_overlap_over_single_list_ranks() -> None:
    version = _version()
    shared = _chunk(version, 0, "shared")
    dense_only = _chunk(version, 1, "dense only")
    sparse_only = _chunk(version, 2, "sparse only")
    fused = ReciprocalRankFusion(k=60).fuse(
        [
            _hit(dense_only, source=RetrievalSource.DENSE, rank=1),
            _hit(shared, source=RetrievalSource.DENSE, rank=2),
        ],
        [
            _hit(shared, source=RetrievalSource.SPARSE, rank=1),
            _hit(sparse_only, source=RetrievalSource.SPARSE, rank=2),
        ],
        limit=10,
    )
    assert [item.chunk_id for item in fused] == [shared.id, dense_only.id, sparse_only.id]
    assert fused[0].fused_rank == 1
    assert fused[0].dense_rank == 2
    assert fused[0].sparse_rank == 1
    assert fused[0].rrf_score == pytest.approx(1 / 62 + 1 / 61)


def test_rrf_fuses_a_surviving_list_when_the_other_is_empty() -> None:
    version = _version()
    only = _chunk(version, 0, "only dense")
    fused = ReciprocalRankFusion(k=60).fuse(
        [_hit(only, source=RetrievalSource.DENSE, rank=1)],
        [],
        limit=5,
    )
    assert len(fused) == 1
    assert fused[0].chunk_id == only.id
    assert fused[0].sparse_rank is None
    assert fused[0].rrf_score == pytest.approx(1 / 61)


def test_rrf_both_empty_returns_no_candidates() -> None:
    assert ReciprocalRankFusion().fuse([], [], limit=5) == []


def test_rrf_deduplicates_repeat_ranks_in_one_list() -> None:
    version = _version()
    chunk = _chunk(version, 0, "dup")
    fused = ReciprocalRankFusion(k=60).fuse(
        [
            _hit(chunk, source=RetrievalSource.DENSE, rank=1, score=0.9),
            _hit(chunk, source=RetrievalSource.DENSE, rank=4, score=0.1),
        ],
        [],
        limit=5,
    )
    assert len(fused) == 1
    assert fused[0].dense_rank == 1
    assert fused[0].dense_score == 0.9


def test_rrf_tie_breaks_by_chunk_id() -> None:
    version = _version()
    left = _chunk(version, 0, "left")
    right = _chunk(version, 1, "right")
    fused = ReciprocalRankFusion(k=60).fuse(
        [_hit(left, source=RetrievalSource.DENSE, rank=1)],
        [_hit(right, source=RetrievalSource.SPARSE, rank=1)],
        limit=5,
    )
    assert [item.chunk_id for item in fused] == sorted([left.id, right.id], key=str)
    assert fused[0].rrf_score == fused[1].rrf_score


def test_rrf_truncates_to_fused_limit() -> None:
    version = _version()
    chunks = [_chunk(version, order, f"t{order}") for order in range(3)]
    dense = [
        _hit(chunk, source=RetrievalSource.DENSE, rank=index)
        for index, chunk in enumerate(chunks, 1)
    ]
    fused = ReciprocalRankFusion(k=60).fuse(dense, [], limit=2)
    assert len(fused) == 2
    assert [item.fused_rank for item in fused] == [1, 2]


def test_rrf_rejects_invalid_rank() -> None:
    version = _version()
    chunk = _chunk(version, 0, "bad")
    with pytest.raises(HybridFusionError, match="rank"):
        ReciprocalRankFusion().fuse(
            [_hit(chunk, source=RetrievalSource.DENSE, rank=0)],
            [],
            limit=5,
        )


def test_rrf_rejects_duplicate_metadata_conflict() -> None:
    version = _version()
    chunk = _chunk(version, 0, "same id")
    conflicting = _hit(chunk, source=RetrievalSource.SPARSE, rank=1)
    object.__setattr__(conflicting, "document_id", uuid4())
    with pytest.raises(HybridFusionError, match="metadata"):
        ReciprocalRankFusion().fuse(
            [_hit(chunk, source=RetrievalSource.DENSE, rank=1)],
            [conflicting],
            limit=5,
        )


@pytest.mark.asyncio
async def test_hybrid_retrieval_returns_fused_candidates() -> None:
    version = _version()
    chunks = [
        _chunk(version, 0, "the cat sat"),
        _chunk(version, 1, "Form POLICY_42 must be signed"),
    ]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    fused = await retrieve_hybrid(
        "POLICY_42",
        embedder=HashEmbeddingProvider(dimension=8),
        encoder=LexicalSparseEncoder(),
        store=store,
        chunks=chunks,
        collection_id=version.collection_id,
        document_version_ids=[version.id],
        top_k=5,
        fusion=ReciprocalRankFusion(k=60),
        fused_top_k=5,
    )
    assert fused
    assert fused[0].chunk_id == chunks[1].id
    assert fused[0].sparse_rank == 1


@pytest.mark.asyncio
async def test_hybrid_empty_hits_on_one_side_still_fuse() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "unrelated prose about weather")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    fused = await retrieve_hybrid(
        "POLICY_42_UNIQUE_TOKEN",
        embedder=HashEmbeddingProvider(dimension=8),
        encoder=LexicalSparseEncoder(),
        store=store,
        chunks=chunks,
        collection_id=version.collection_id,
        document_version_ids=[version.id],
        top_k=5,
        fusion=ReciprocalRankFusion(k=60),
        fused_top_k=5,
    )
    assert len(fused) == 1
    assert fused[0].chunk_id == chunks[0].id
    assert fused[0].sparse_rank is None
    assert fused[0].dense_rank == 1


@pytest.mark.asyncio
async def test_dense_unavailable_fails_closed() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "Form POLICY_42 must be signed")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    with pytest.raises(DenseRetrievalError, match="timed out"):
        await retrieve_hybrid(
            "POLICY_42",
            embedder=_TimeoutEmbedder(dimension=8),
            encoder=LexicalSparseEncoder(),
            store=store,
            chunks=chunks,
            collection_id=version.collection_id,
            document_version_ids=[version.id],
            top_k=5,
            fusion=ReciprocalRankFusion(),
            fused_top_k=5,
        )


@pytest.mark.asyncio
async def test_sparse_unavailable_fails_closed() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "Form POLICY_42 must be signed")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    with pytest.raises(SparseRetrievalError, match="timed out"):
        await retrieve_hybrid(
            "POLICY_42",
            embedder=HashEmbeddingProvider(dimension=8),
            encoder=_TimeoutEncoder(),
            store=store,
            chunks=chunks,
            collection_id=version.collection_id,
            document_version_ids=[version.id],
            top_k=5,
            fusion=ReciprocalRankFusion(),
            fused_top_k=5,
        )


@pytest.mark.asyncio
async def test_evaluation_ablation_skips_dense_without_production_fallback() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "Form POLICY_42 must be signed")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    fused = await retrieve_hybrid(
        "POLICY_42",
        embedder=_TimeoutEmbedder(dimension=8),
        encoder=LexicalSparseEncoder(),
        store=store,
        chunks=chunks,
        collection_id=version.collection_id,
        document_version_ids=[version.id],
        top_k=5,
        fusion=ReciprocalRankFusion(),
        fused_top_k=5,
        evaluation=EvaluationRunConfig(include_dense=False, include_sparse=True),
    )
    assert fused
    assert fused[0].dense_rank is None
    assert fused[0].sparse_rank == 1
