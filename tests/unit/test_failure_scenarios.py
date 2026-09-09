from __future__ import annotations

from uuid import uuid4

import pytest

from cited_rag.adapters.embedding.hashing import HashEmbeddingProvider
from cited_rag.adapters.generation.heuristic import HeuristicGroundedGenerator
from cited_rag.adapters.retrieval.memory import MemoryRetrievalStore
from cited_rag.adapters.sparse.lexical import LexicalSparseEncoder
from cited_rag.application.citations import validate_citations
from cited_rag.application.context import serialize_model_evidence
from cited_rag.application.generation import generate_grounded_answer
from cited_rag.application.indexing import persist_dense_index
from cited_rag.application.query import answer_question
from cited_rag.application.rerank import rerank_candidates
from cited_rag.application.retrieval import retrieve_dense
from cited_rag.config import Settings
from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.enums import AnswerStatus
from cited_rag.domain.exceptions import (
    CitationValidationError,
    DenseRetrievalError,
    GenerationError,
    RerankerError,
)
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.document import DocumentVersion
from cited_rag.domain.models.evidence import EvidencePackage, EvidenceRecord
from cited_rag.domain.models.generation import Claim, GroundedGenerationResult
from cited_rag.domain.models.retrieval import FusedCandidate


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


def _chunk(version: DocumentVersion, text: str = "Employees receive 20 days of leave.") -> Chunk:
    return Chunk(
        collection_id=version.collection_id,
        document_id=version.document_id,
        document_version_id=version.id,
        page_start=1,
        page_end=1,
        chunk_order=0,
        text=text,
        content_hash="h0",
    )


class _TimeoutReranker:
    async def rerank(self, query: str, candidates: object, top_n: int) -> list:
        raise TimeoutError("reranker timed out")


class _TimeoutGenerator:
    async def generate(self, prompt: object) -> object:
        raise TimeoutError("generation timed out")


@pytest.mark.asyncio
async def test_qdrant_search_failure_is_not_insufficient_evidence() -> None:
    version = _version()
    chunk = _chunk(version)
    store = MemoryRetrievalStore()
    await persist_dense_index(
        [chunk],
        embedder=HashEmbeddingProvider(dimension=8),
        store=store,
        config=EmbeddingConfig(dimension=8),
    )
    store.fail_search = True
    with pytest.raises(DenseRetrievalError):
        await retrieve_dense(
            "How much leave?",
            embedder=HashEmbeddingProvider(dimension=8),
            store=store,
            chunks=[chunk],
            collection_id=version.collection_id,
            document_version_ids=[version.id],
            top_k=5,
        )


@pytest.mark.asyncio
async def test_reranker_timeout_is_reranker_error() -> None:
    version = _version()
    chunk = _chunk(version)
    fused = FusedCandidate(
        chunk_id=chunk.id,
        rrf_score=0.1,
        fused_rank=1,
        collection_id=chunk.collection_id,
        document_id=chunk.document_id,
        document_version_id=chunk.document_version_id,
        page_start=1,
        page_end=1,
        text=chunk.text,
        dense_rank=1,
        dense_score=1.0,
        sparse_rank=None,
        sparse_score=None,
    )
    with pytest.raises(RerankerError, match="timed out"):
        await rerank_candidates(
            "leave",
            [fused],
            reranker=_TimeoutReranker(),  # type: ignore[arg-type]
            top_n=5,
            timeout_seconds=1,
        )


@pytest.mark.asyncio
async def test_generation_timeout_is_not_no_answer() -> None:
    record = EvidenceRecord(
        evidence_id="E1",
        chunk_id=uuid4(),
        collection_id=uuid4(),
        document_id=uuid4(),
        document_version_id=uuid4(),
        document_name="a.pdf",
        page_start=1,
        page_end=1,
        text="leave",
    )
    package = EvidencePackage(
        records=(record,),
        model_context=serialize_model_evidence((record,)),
        dropped_chunk_ids=(),
    )
    with pytest.raises(GenerationError, match="timed out"):
        await generate_grounded_answer(
            "leave",
            package,
            generator=_TimeoutGenerator(),  # type: ignore[arg-type]
            timeout_seconds=1,
        )


def test_invented_evidence_id_fails_closed() -> None:
    record = EvidenceRecord(
        evidence_id="E1",
        chunk_id=uuid4(),
        collection_id=uuid4(),
        document_id=uuid4(),
        document_version_id=uuid4(),
        document_name="a.pdf",
        page_start=1,
        page_end=1,
        text="leave",
    )
    package = EvidencePackage(
        records=(record,),
        model_context=serialize_model_evidence((record,)),
        dropped_chunk_ids=(),
    )
    with pytest.raises(CitationValidationError):
        validate_citations(
            GroundedGenerationResult(
                status=AnswerStatus.ANSWERED,
                answer="x",
                claims=(Claim(text="x", evidence_ids=("E99",)),),
                model="scripted",
            ),
            package,
            collection_id=record.collection_id,
        )


@pytest.mark.asyncio
async def test_cross_collection_query_returns_no_hits() -> None:
    version = _version()
    other = uuid4()
    chunk = _chunk(version)
    store = MemoryRetrievalStore()
    await persist_dense_index(
        [chunk],
        embedder=HashEmbeddingProvider(dimension=8),
        store=store,
        config=EmbeddingConfig(dimension=8),
    )
    hits = await retrieve_dense(
        "leave",
        embedder=HashEmbeddingProvider(dimension=8),
        store=store,
        chunks=[chunk],
        collection_id=other,
        document_version_ids=[version.id],
        top_k=5,
    )
    assert hits == []


@pytest.mark.asyncio
async def test_zero_ready_versions_is_insufficient_not_error() -> None:
    version = _version()
    outcome = await answer_question(
        "How much leave?",
        collection_id=version.collection_id,
        document_version_ids=[],
        chunks=[],
        document_names={},
        embedder=HashEmbeddingProvider(dimension=8),
        encoder=LexicalSparseEncoder(),
        store=MemoryRetrievalStore(),
        reranker=_TimeoutReranker(),  # type: ignore[arg-type]
        generator=HeuristicGroundedGenerator(),
        settings=Settings.model_validate({"embedding_dimension": 8}),
    )
    assert outcome.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert outcome.reason is not None
