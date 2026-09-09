from __future__ import annotations

import asyncio
from collections.abc import Sequence
from uuid import uuid4

import pytest

from cited_rag.adapters.rerank import create_reranker
from cited_rag.adapters.rerank.overlap import LexicalOverlapReranker
from cited_rag.application.rerank import rerank_candidates
from cited_rag.config import Settings
from cited_rag.domain.exceptions import RerankerError
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.document import DocumentVersion
from cited_rag.domain.models.evaluation import EvaluationRunConfig
from cited_rag.domain.models.retrieval import FusedCandidate, RerankedEvidence
from cited_rag.ports.reranker import Reranker


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


def _fused(chunk: Chunk, *, fused_rank: int, rrf_score: float = 0.1) -> FusedCandidate:
    return FusedCandidate(
        chunk_id=chunk.id,
        rrf_score=rrf_score,
        fused_rank=fused_rank,
        collection_id=chunk.collection_id,
        document_id=chunk.document_id,
        document_version_id=chunk.document_version_id,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        text=chunk.text,
        dense_rank=fused_rank,
        dense_score=1.0,
        sparse_rank=None,
        sparse_score=None,
    )


class _TimeoutReranker:
    async def rerank(
        self,
        query: str,
        candidates: Sequence[FusedCandidate],
        top_n: int,
    ) -> list:
        await asyncio.sleep(1)
        return []


class _BoomReranker:
    async def rerank(
        self,
        query: str,
        candidates: Sequence[FusedCandidate],
        top_n: int,
    ) -> list:
        raise RuntimeError("provider down")


@pytest.mark.asyncio
async def test_overlap_reranker_reorders_by_query_tokens() -> None:
    version = _version()
    weather = _chunk(version, 0, "unrelated weather notes")
    policy = _chunk(version, 1, "Form POLICY_42 must be signed")
    ranked = await rerank_candidates(
        "POLICY_42 form",
        [_fused(weather, fused_rank=1), _fused(policy, fused_rank=2)],
        reranker=LexicalOverlapReranker(),
        top_n=10,
        timeout_seconds=1,
    )
    assert [item.chunk_id for item in ranked] == [policy.id, weather.id]
    assert ranked[0].rerank_rank == 1
    assert ranked[0].fused_rank == 2
    assert ranked[0].reranker_name == "lexical-overlap"
    assert ranked[0].chunk_id == policy.id


@pytest.mark.asyncio
async def test_rerank_truncates_shortlist() -> None:
    version = _version()
    chunks = [_chunk(version, order, f"token{order} extra") for order in range(3)]
    ranked = await rerank_candidates(
        "token0",
        [_fused(chunk, fused_rank=order + 1) for order, chunk in enumerate(chunks)],
        reranker=LexicalOverlapReranker(),
        top_n=1,
        timeout_seconds=1,
    )
    assert len(ranked) == 1
    assert ranked[0].chunk_id == chunks[0].id


@pytest.mark.asyncio
async def test_rerank_empty_list_returns_empty() -> None:
    ranked = await rerank_candidates(
        "q",
        [],
        reranker=LexicalOverlapReranker(),
        top_n=5,
        timeout_seconds=1,
    )
    assert ranked == []


@pytest.mark.asyncio
async def test_reranker_timeout_is_reranker_error() -> None:
    version = _version()
    chunk = _chunk(version, 0, "Form POLICY_42")
    with pytest.raises(RerankerError, match="timed out"):
        await rerank_candidates(
            "POLICY_42",
            [_fused(chunk, fused_rank=1)],
            reranker=_TimeoutReranker(),  # type: ignore[arg-type]
            top_n=5,
            timeout_seconds=0.01,
        )


@pytest.mark.asyncio
async def test_reranker_provider_failure_is_reranker_error() -> None:
    version = _version()
    chunk = _chunk(version, 0, "Form POLICY_42")
    with pytest.raises(RerankerError, match="reranker failed"):
        await rerank_candidates(
            "POLICY_42",
            [_fused(chunk, fused_rank=1)],
            reranker=_BoomReranker(),  # type: ignore[arg-type]
            top_n=5,
            timeout_seconds=1,
        )


@pytest.mark.asyncio
async def test_missing_text_is_reranker_error() -> None:
    version = _version()
    chunk = _chunk(version, 0, "ok")
    blank = _fused(chunk, fused_rank=1)
    object.__setattr__(blank, "text", "   ")
    with pytest.raises(RerankerError, match="text"):
        await rerank_candidates(
            "ok",
            [blank],
            reranker=LexicalOverlapReranker(),
            top_n=5,
            timeout_seconds=1,
        )


@pytest.mark.asyncio
async def test_evaluation_can_disable_rerank_without_calling_provider() -> None:
    version = _version()
    first = _chunk(version, 0, "unrelated weather notes")
    second = _chunk(version, 1, "Form POLICY_42 must be signed")
    ranked = await rerank_candidates(
        "POLICY_42",
        [_fused(first, fused_rank=1), _fused(second, fused_rank=2)],
        reranker=_BoomReranker(),  # type: ignore[arg-type]
        top_n=5,
        timeout_seconds=1,
        evaluation=EvaluationRunConfig(include_rerank=False),
    )
    assert [item.chunk_id for item in ranked] == [first.id, second.id]
    assert ranked[0].reranker_name == "disabled"


class _UnknownChunkReranker:
    async def rerank(
        self,
        query: str,
        candidates: Sequence[FusedCandidate],
        top_n: int,
    ) -> list[RerankedEvidence]:
        item = candidates[0]
        return [
            RerankedEvidence(
                chunk_id=uuid4(),
                rerank_score=1.0,
                rerank_rank=1,
                fused_rank=item.fused_rank,
                rrf_score=item.rrf_score,
                collection_id=item.collection_id,
                document_id=item.document_id,
                document_version_id=item.document_version_id,
                page_start=item.page_start,
                page_end=item.page_end,
                text=item.text,
                dense_rank=item.dense_rank,
                dense_score=item.dense_score,
                sparse_rank=item.sparse_rank,
                sparse_score=item.sparse_score,
                reranker_name="fake",
                reranker_version="v1",
            )
        ]


@pytest.mark.asyncio
async def test_unknown_rerank_chunk_is_reranker_error() -> None:
    version = _version()
    chunk = _chunk(version, 0, "Form POLICY_42")
    with pytest.raises(RerankerError, match="unknown chunk"):
        await rerank_candidates(
            "POLICY_42",
            [_fused(chunk, fused_rank=1)],
            reranker=_UnknownChunkReranker(),  # type: ignore[arg-type]
            top_n=5,
            timeout_seconds=1,
        )


def test_factory_builds_overlap_reranker() -> None:
    reranker: Reranker = create_reranker(Settings(_env_file=None))
    assert isinstance(reranker, LexicalOverlapReranker)
