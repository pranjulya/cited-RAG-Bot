from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from cited_rag.evaluation.run import persist_manifest, run_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run layered RAG evaluation")
    parser.add_argument("--dataset", default="evaluation/golden/v1.json")
    parser.add_argument("--out", default="evaluation/results/latest.json")
    args = parser.parse_args()
    manifest = asyncio.run(run_evaluation(Path(args.dataset)))
    persist_manifest(manifest, Path(args.out))
    layers = manifest.layers
    print(f"dataset={manifest.dataset_version} config={manifest.config} cases={layers.cases}")
    print(
        "retrieval "
        f"recall@5={layers.recall_at_5:.3f} mrr={layers.mrr:.3f} ndcg@5={layers.ndcg_at_5:.3f}"
    )
    print(
        "quality "
        f"citation_validity={layers.citation_validity:.3f} "
        f"no_answer_p={layers.no_answer_precision:.3f} "
        f"no_answer_r={layers.no_answer_recall:.3f} "
        f"false_answer={layers.false_answer_rate:.3f} "
        f"latency_ms={layers.latency_ms}"
    )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
