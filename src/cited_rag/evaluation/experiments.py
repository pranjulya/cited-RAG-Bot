from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from cited_rag.adapters.embedding.hashing import HashEmbeddingProvider
from cited_rag.adapters.generation.heuristic import HeuristicGroundedGenerator
from cited_rag.adapters.rerank.overlap import LexicalOverlapReranker
from cited_rag.adapters.retrieval.memory import MemoryRetrievalStore
from cited_rag.adapters.sparse.lexical import LexicalSparseEncoder
from cited_rag.application.indexing import persist_dense_index, persist_sparse_index
from cited_rag.application.query import answer_question
from cited_rag.config import Settings
from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.enums import AnswerStatus
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.document import DocumentVersion
from cited_rag.domain.models.evaluation import EvaluationRunConfig
from cited_rag.evaluation.dataset import GoldenDataset, load_golden_dataset

CONFIGS = {
    "dense-only": EvaluationRunConfig(
        include_dense=True, include_sparse=False, include_rerank=False
    ),
    "sparse-only": EvaluationRunConfig(
        include_dense=False, include_sparse=True, include_rerank=False
    ),
    "hybrid": EvaluationRunConfig(include_dense=True, include_sparse=True, include_rerank=False),
    "hybrid-rerank": EvaluationRunConfig(
        include_dense=True, include_sparse=True, include_rerank=True
    ),
}


@dataclass(frozen=True, slots=True)
class ExperimentScore:
    name: str
    answered: int
    abstained: int
    cases: int


async def run_v1_matrix(dataset: GoldenDataset | None = None) -> list[ExperimentScore]:
    gold = dataset or load_golden_dataset(Path("evaluation/golden/v1.json"))
    version = DocumentVersion(
        document_id=uuid4(),
        collection_id=uuid4(),
        version_number=1,
        content_hash="eval",
        original_filename="eval.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        storage_uri="local://eval.pdf",
    )
    chunks = [
        Chunk(
            collection_id=version.collection_id,
            document_id=version.document_id,
            document_version_id=version.id,
            page_start=1,
            page_end=1,
            chunk_order=0,
            text="Employees receive 20 days of leave.",
            content_hash="h0",
        )
    ]
    store = MemoryRetrievalStore()
    config = EmbeddingConfig(dimension=8)
    await persist_dense_index(
        chunks, embedder=HashEmbeddingProvider(dimension=8), store=store, config=config
    )
    await persist_sparse_index(chunks, encoder=LexicalSparseEncoder(), store=store, config=config)
    settings = Settings.model_validate({"embedding_dimension": 8})
    scores: list[ExperimentScore] = []
    for name, evaluation in CONFIGS.items():
        answered = 0
        abstained = 0
        for case in gold.cases:
            outcome = await answer_question(
                case.question,
                collection_id=version.collection_id,
                document_version_ids=[version.id],
                chunks=chunks,
                document_names={version.document_id: "eval.pdf"},
                embedder=HashEmbeddingProvider(dimension=8),
                encoder=LexicalSparseEncoder(),
                store=store,
                reranker=LexicalOverlapReranker(),
                generator=HeuristicGroundedGenerator(),
                settings=settings,
                evaluation=evaluation,
            )
            if outcome.status is AnswerStatus.ANSWERED:
                answered += 1
            else:
                abstained += 1
        scores.append(
            ExperimentScore(
                name=name, answered=answered, abstained=abstained, cases=len(gold.cases)
            )
        )
    return scores


def recommended_defaults() -> str:
    return (
        "V1 production path remains hybrid RRF plus rerank. Hash embeddings and "
        "the heuristic generator are not quality evidence for model choice; they "
        "only prove the ablation wiring. Keep CITED_RAG_RRF_K=60 and "
        "CITED_RAG_RERANK_TOP_N=10 until a hosted encoder/reranker is measured."
    )
