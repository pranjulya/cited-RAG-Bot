from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from cited_rag.adapters.embedding.hashing import HashEmbeddingProvider
from cited_rag.adapters.generation.heuristic import HeuristicGroundedGenerator
from cited_rag.adapters.rerank.overlap import LexicalOverlapReranker
from cited_rag.adapters.retrieval.memory import MemoryRetrievalStore
from cited_rag.adapters.sparse.lexical import LexicalSparseEncoder
from cited_rag.application.indexing import persist_dense_index, persist_sparse_index
from cited_rag.application.query import answer_question
from cited_rag.config import Settings
from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.enums import AnswerStatus, NoAnswerReason
from cited_rag.domain.exceptions import DecisionProviderError
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.decision import EvidenceDecision
from cited_rag.domain.models.document import DocumentVersion
from cited_rag.domain.models.evidence import EvidencePackage
from cited_rag.main import create_app


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


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        embedding_dimension=8,
        retrieval_top_k=5,
        fused_top_k=5,
        rerank_top_n=5,
        max_evidence_items=8,
        context_token_budget=500,
    )


class _ShadowDecisioner:
    def __init__(self, *, failure: bool = False) -> None:
        self.failure = failure
        self.calls: list[tuple[str, EvidencePackage]] = []

    async def decide(self, question: str, evidence: EvidencePackage) -> EvidenceDecision:
        self.calls.append((question, evidence))
        if self.failure:
            raise DecisionProviderError("provider unavailable")
        return EvidenceDecision(answerable_probability=0.9, model="test-jev")


@pytest.mark.asyncio
async def test_answerable_query_returns_validated_citations() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "Employees receive 20 days of leave.")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    outcome = await answer_question(
        "How much leave?",
        collection_id=version.collection_id,
        document_version_ids=[version.id],
        chunks=chunks,
        document_names={version.document_id: "handbook.pdf"},
        embedder=HashEmbeddingProvider(dimension=8),
        encoder=LexicalSparseEncoder(),
        store=store,
        reranker=LexicalOverlapReranker(),
        generator=HeuristicGroundedGenerator(),
        settings=_settings(),
    )
    assert outcome.status is AnswerStatus.ANSWERED
    assert "20 days" in outcome.answer
    assert len(outcome.citations) == 1
    assert outcome.citations[0].document_name == "handbook.pdf"
    assert outcome.citations[0].page_start == 1
    assert not hasattr(outcome.citations[0], "chunk_id")
    assert outcome.evidence[0].evidence_id == "E1"
    assert outcome.evidence[0].text == "Employees receive 20 days of leave."


@pytest.mark.asyncio
async def test_unsupported_query_is_insufficient_evidence() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "Employees receive 20 days of leave.")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    outcome = await answer_question(
        "What is the nuclear launch code?",
        collection_id=version.collection_id,
        document_version_ids=[version.id],
        chunks=chunks,
        document_names={version.document_id: "handbook.pdf"},
        embedder=HashEmbeddingProvider(dimension=8),
        encoder=LexicalSparseEncoder(),
        store=store,
        reranker=LexicalOverlapReranker(),
        generator=HeuristicGroundedGenerator(),
        settings=_settings(),
    )
    assert outcome.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert outcome.citations == ()
    assert outcome.reason is not None


@pytest.mark.asyncio
async def test_shadow_decision_does_not_change_answer_or_citations() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "Employees receive 20 days of leave.")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    decisioner = _ShadowDecisioner()

    outcome = await answer_question(
        "How much leave?",
        collection_id=version.collection_id,
        document_version_ids=[version.id],
        chunks=chunks,
        document_names={version.document_id: "handbook.pdf"},
        embedder=HashEmbeddingProvider(dimension=8),
        encoder=LexicalSparseEncoder(),
        store=store,
        reranker=LexicalOverlapReranker(),
        generator=HeuristicGroundedGenerator(),
        settings=_settings(),
        decisioner=decisioner,
    )

    assert outcome.status is AnswerStatus.ANSWERED
    assert len(outcome.citations) == 1
    assert len(decisioner.calls) == 1
    assert decisioner.calls[0][0] == "How much leave?"
    assert decisioner.calls[0][1].records[0].evidence_id == "E1"


@pytest.mark.asyncio
async def test_shadow_provider_failure_does_not_change_no_answer() -> None:
    version = _version()
    chunks = [_chunk(version, 0, "Employees receive 20 days of leave.")]
    store = MemoryRetrievalStore()
    await _index(version, chunks, store)
    decisioner = _ShadowDecisioner(failure=True)

    outcome = await answer_question(
        "What is the nuclear launch code?",
        collection_id=version.collection_id,
        document_version_ids=[version.id],
        chunks=chunks,
        document_names={version.document_id: "handbook.pdf"},
        embedder=HashEmbeddingProvider(dimension=8),
        encoder=LexicalSparseEncoder(),
        store=store,
        reranker=LexicalOverlapReranker(),
        generator=HeuristicGroundedGenerator(),
        settings=_settings(),
        decisioner=decisioner,
    )

    assert outcome.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert outcome.citations == ()
    assert len(decisioner.calls) == 1


@pytest.mark.asyncio
async def test_zero_ready_versions_is_no_ready_documents() -> None:
    version = _version()
    decisioner = _ShadowDecisioner()
    outcome = await answer_question(
        "How much leave?",
        collection_id=version.collection_id,
        document_version_ids=[],
        chunks=[],
        document_names={},
        embedder=HashEmbeddingProvider(dimension=8),
        encoder=LexicalSparseEncoder(),
        store=MemoryRetrievalStore(),
        reranker=LexicalOverlapReranker(),
        generator=HeuristicGroundedGenerator(),
        settings=_settings(),
        decisioner=decisioner,
    )
    assert outcome.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert outcome.reason is NoAnswerReason.NO_READY_DOCUMENTS
    assert outcome.evidence == ()
    assert decisioner.calls == []


def test_query_route_requires_bearer() -> None:
    settings = Settings(_env_file=None, api_key="test-placeholder-key", environment="test")
    client = TestClient(create_app(settings))
    missing = client.post(
        f"/v1/collections/{uuid4()}/query",
        json={"question": "How much leave?"},
    )
    assert missing.status_code == 401


def test_query_route_too_long_is_413_not_pydantic_422() -> None:
    from cited_rag.api.deps import get_principal, get_uow
    from cited_rag.domain.models.principal import ApiPrincipal

    settings = Settings(
        _env_file=None,
        api_key="test-placeholder-key",
        environment="test",
        query_max_chars=8,
    )
    app = create_app(settings)

    async def _uow() -> object:
        yield object()

    async def _principal() -> ApiPrincipal:
        return ApiPrincipal(name="test")

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_principal] = _principal
    client = TestClient(app)
    response = client.post(
        f"/v1/collections/{uuid4()}/query",
        json={"question": "123456789"},
        headers={"Authorization": "Bearer test-placeholder-key"},
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "query_too_long"
