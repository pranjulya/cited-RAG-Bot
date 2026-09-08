from __future__ import annotations

from uuid import uuid4

from cited_rag.application.context import build_evidence_package, estimate_tokens
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.document import DocumentVersion
from cited_rag.domain.models.retrieval import RerankedEvidence


def _version() -> DocumentVersion:
    return DocumentVersion(
        document_id=uuid4(),
        collection_id=uuid4(),
        version_number=1,
        content_hash="h",
        original_filename="handbook.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        storage_uri="local://a.pdf",
    )


def _chunk(version: DocumentVersion, order: int, text: str) -> Chunk:
    return Chunk(
        collection_id=version.collection_id,
        document_id=version.document_id,
        document_version_id=version.id,
        page_start=order + 1,
        page_end=order + 1,
        chunk_order=order,
        text=text,
        content_hash=f"h{order}",
    )


def _reranked(chunk: Chunk, rank: int, score: float = 2.0) -> RerankedEvidence:
    return RerankedEvidence(
        chunk_id=chunk.id,
        rerank_score=score,
        rerank_rank=rank,
        fused_rank=rank,
        rrf_score=0.1,
        collection_id=chunk.collection_id,
        document_id=chunk.document_id,
        document_version_id=chunk.document_version_id,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        text=chunk.text,
        dense_rank=rank,
        dense_score=1.0,
        sparse_rank=None,
        sparse_score=None,
        reranker_name="lexical-overlap",
        reranker_version="v1",
    )


def test_assigns_stable_evidence_ids_in_rerank_order() -> None:
    version = _version()
    first = _chunk(version, 0, "leave policy")
    second = _chunk(version, 1, "sick policy")
    package = build_evidence_package(
        [_reranked(first, 1), _reranked(second, 2)],
        max_items=8,
        token_budget=500,
        document_names={version.document_id: "handbook.pdf"},
    )
    assert [record.evidence_id for record in package.records] == ["E1", "E2"]
    assert package.records[0].chunk_id == first.id
    assert package.records[0].document_name == "handbook.pdf"
    assert "E1" in package.model_context
    assert "leave policy" in package.model_context
    assert str(first.id) not in package.model_context
    assert "handbook.pdf" not in package.model_context
    assert "page" not in package.model_context.lower()


def test_deduplicates_chunk_ids_keeping_first() -> None:
    version = _version()
    chunk = _chunk(version, 0, "once")
    package = build_evidence_package(
        [_reranked(chunk, 1), _reranked(chunk, 2)],
        max_items=8,
        token_budget=500,
    )
    assert len(package.records) == 1
    assert package.dropped_chunk_ids == (chunk.id,)


def test_trims_to_item_and_token_budget() -> None:
    version = _version()
    short = _chunk(version, 0, "short")
    huge = _chunk(version, 1, "x" * 400)
    third = _chunk(version, 2, "also short")
    limited = build_evidence_package(
        [_reranked(short, 1), _reranked(third, 3)],
        max_items=1,
        token_budget=500,
    )
    assert [record.chunk_id for record in limited.records] == [short.id]
    assert third.id in limited.dropped_chunk_ids
    tight = build_evidence_package(
        [_reranked(short, 1), _reranked(huge, 2)],
        max_items=8,
        token_budget=estimate_tokens("[E1]\nEvidence:\nshort") + 5,
    )
    assert [record.chunk_id for record in tight.records] == [short.id]
    assert huge.id in tight.dropped_chunk_ids


def test_oversized_chunk_is_dropped() -> None:
    version = _version()
    huge = _chunk(version, 0, "y" * 800)
    package = build_evidence_package(
        [_reranked(huge, 1)],
        max_items=8,
        token_budget=10,
    )
    assert package.records == ()
    assert package.model_context == ""
    assert package.dropped_chunk_ids == (huge.id,)


def test_empty_candidates_yield_empty_package() -> None:
    package = build_evidence_package([], max_items=8, token_budget=100)
    assert package.records == ()
    assert package.model_context == ""
