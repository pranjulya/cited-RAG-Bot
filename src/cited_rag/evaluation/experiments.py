from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cited_rag.domain.models.evaluation import EvaluationRunConfig
from cited_rag.evaluation.dataset import GoldenDataset
from cited_rag.evaluation.run import LayerResults, run_evaluation

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
    recall_at_5: float
    mrr: float
    ndcg_at_5: float
    citation_validity: float
    false_answer_rate: float
    latency_ms: int
    cases: int


async def run_v1_matrix(dataset: GoldenDataset | None = None) -> list[ExperimentScore]:
    _ = dataset
    scores: list[ExperimentScore] = []
    for name, evaluation in CONFIGS.items():
        manifest = await run_evaluation(
            Path("evaluation/golden/v1.json"),
            evaluation=evaluation,
            config_name=name,
        )
        layers: LayerResults = manifest.layers
        scores.append(
            ExperimentScore(
                name=name,
                recall_at_5=layers.recall_at_5,
                mrr=layers.mrr,
                ndcg_at_5=layers.ndcg_at_5,
                citation_validity=layers.citation_validity,
                false_answer_rate=layers.false_answer_rate,
                latency_ms=layers.latency_ms,
                cases=layers.cases,
            )
        )
    return scores


def recommended_defaults(scores: list[ExperimentScore] | None = None) -> str:
    hybrid = next((item for item in scores or [] if item.name == "hybrid-rerank"), None)
    measured = ""
    if hybrid is not None:
        measured = (
            f" On golden-v1, hybrid-rerank recall@5={hybrid.recall_at_5:.3f} "
            f"mrr={hybrid.mrr:.3f} ndcg@5={hybrid.ndcg_at_5:.3f} "
            f"false_answer={hybrid.false_answer_rate:.3f}."
        )
    return (
        "V1 production path remains hybrid RRF plus rerank."
        + measured
        + " Hash embeddings and the heuristic generator are not a reason to change "
        "ADR-011. Keep CITED_RAG_RRF_K=60 and CITED_RAG_RERANK_TOP_N=10 until a "
        "hosted encoder/reranker is measured."
    )
