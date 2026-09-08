from __future__ import annotations

from pathlib import Path

from cited_rag.evaluation.dataset import load_golden_dataset
from cited_rag.evaluation.metrics import mrr, ndcg_at_k, recall_at_k


def main() -> None:
    path = Path("evaluation/golden/v1.json")
    dataset = load_golden_dataset(path)
    print(f"dataset={dataset.version} cases={len(dataset.cases)}")
    print("metrics=recall_at_k,mrr,ndcg_at_k (pass retrieved ids at runtime)")
    _ = (recall_at_k, mrr, ndcg_at_k)


if __name__ == "__main__":
    main()
