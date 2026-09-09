from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from uuid import uuid4

from cited_rag.adapters.embedding.hashing import HashEmbeddingProvider
from cited_rag.adapters.generation.heuristic import HeuristicGroundedGenerator
from cited_rag.adapters.rerank.overlap import LexicalOverlapReranker
from cited_rag.adapters.retrieval.memory import MemoryRetrievalStore
from cited_rag.adapters.sparse.lexical import LexicalSparseEncoder
from cited_rag.application.citations import validate_citations
from cited_rag.application.context import build_evidence_package
from cited_rag.application.generation import generate_grounded_answer
from cited_rag.application.indexing import persist_dense_index, persist_sparse_index
from cited_rag.application.rerank import rerank_candidates
from cited_rag.application.retrieval import ReciprocalRankFusion, retrieve_hybrid
from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.enums import AnswerStatus
from cited_rag.domain.exceptions import CitationValidationError
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.document import DocumentVersion
from cited_rag.domain.models.evaluation import EvaluationRunConfig
from cited_rag.evaluation.dataset import GoldenDataset, load_golden_dataset
from cited_rag.evaluation.metrics import (
    false_answer_rate,
    mrr,
    ndcg_at_k,
    no_answer_precision,
    no_answer_recall,
    recall_at_k,
)


@dataclass
class LayerResults:
    recall_at_5: float
    mrr: float
    ndcg_at_5: float
    citation_validity: float
    no_answer_precision: float
    no_answer_recall: float
    false_answer_rate: float
    latency_ms: int
    cases: int


@dataclass
class EvaluationManifest:
    dataset_version: str
    config: str
    layers: LayerResults
    case_ids: list[str] = field(default_factory=list)


async def run_evaluation(
    dataset_path: Path = Path("evaluation/golden/v1.json"),
    *,
    evaluation: EvaluationRunConfig | None = None,
    config_name: str = "hybrid-rerank",
) -> EvaluationManifest:
    dataset = load_golden_dataset(dataset_path)
    version, chunks, store = await _index_corpus(dataset)
    run = evaluation or EvaluationRunConfig()
    started = time.perf_counter()
    recalls: list[float] = []
    mrrs: list[float] = []
    ndcgs: list[float] = []
    citation_ok = 0
    citation_n = 0
    abstained = 0
    abstained_correct = 0
    unanswerable = 0
    answered_unanswerable = 0
    for case in dataset.cases:
        fused = await retrieve_hybrid(
            case.question,
            embedder=HashEmbeddingProvider(dimension=8),
            encoder=LexicalSparseEncoder(),
            store=store,
            chunks=chunks,
            collection_id=version.collection_id,
            document_version_ids=[version.id],
            top_k=5,
            fusion=ReciprocalRankFusion(k=60),
            fused_top_k=5,
            evaluation=run,
        )
        relevant = {chunk.id for chunk in chunks if chunk.text in case.relevant_texts}
        retrieved_ids = [item.chunk_id for item in fused]
        recalls.append(recall_at_k(retrieved_ids, relevant, 5))
        mrrs.append(mrr(retrieved_ids, relevant))
        ndcgs.append(ndcg_at_k(retrieved_ids, relevant, 5))
        reranked = await rerank_candidates(
            case.question,
            fused,
            reranker=LexicalOverlapReranker(),
            top_n=5,
            timeout_seconds=1,
            evaluation=run,
        )
        evidence = build_evidence_package(
            reranked,
            max_items=8,
            token_budget=1500,
            document_names={version.document_id: "eval.pdf"},
        )
        generated = await generate_grounded_answer(
            case.question,
            evidence,
            generator=HeuristicGroundedGenerator(),
            timeout_seconds=1,
        )
        citation_n += 1
        try:
            validate_citations(
                generated,
                evidence,
                collection_id=version.collection_id,
                allowed_version_ids={version.id},
            )
            citation_ok += 1
        except CitationValidationError:
            pass
        answered = generated.status is AnswerStatus.ANSWERED
        if generated.status is AnswerStatus.INSUFFICIENT_EVIDENCE:
            abstained += 1
            if not case.answerable:
                abstained_correct += 1
        if not case.answerable:
            unanswerable += 1
            if answered:
                answered_unanswerable += 1
    latency_ms = int((time.perf_counter() - started) * 1000)
    layers = LayerResults(
        recall_at_5=_mean(recalls),
        mrr=_mean(mrrs),
        ndcg_at_5=_mean(ndcgs),
        citation_validity=citation_ok / citation_n if citation_n else 1.0,
        no_answer_precision=no_answer_precision(abstained, abstained_correct),
        no_answer_recall=no_answer_recall(unanswerable, abstained_correct),
        false_answer_rate=false_answer_rate(unanswerable, answered_unanswerable),
        latency_ms=latency_ms,
        cases=len(dataset.cases),
    )
    return EvaluationManifest(
        dataset_version=dataset.version,
        config=config_name,
        layers=layers,
        case_ids=[case.id for case in dataset.cases],
    )


def persist_manifest(manifest: EvaluationManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(manifest), indent=2) + "\n", encoding="utf-8")


async def _index_corpus(
    dataset: GoldenDataset,
) -> tuple[DocumentVersion, list[Chunk], MemoryRetrievalStore]:
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
    texts = ["Employees receive 20 days of leave.", "Office hours are posted on intranet."]
    for case in dataset.cases:
        texts.extend(case.relevant_texts)
    unique = list(dict.fromkeys(texts))
    chunks = [
        Chunk(
            collection_id=version.collection_id,
            document_id=version.document_id,
            document_version_id=version.id,
            page_start=1,
            page_end=1,
            chunk_order=order,
            text=text,
            content_hash=f"h{order}",
        )
        for order, text in enumerate(unique)
    ]
    store = MemoryRetrievalStore()
    config = EmbeddingConfig(dimension=8)
    await persist_dense_index(
        chunks, embedder=HashEmbeddingProvider(dimension=8), store=store, config=config
    )
    await persist_sparse_index(chunks, encoder=LexicalSparseEncoder(), store=store, config=config)
    return version, chunks, store


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
