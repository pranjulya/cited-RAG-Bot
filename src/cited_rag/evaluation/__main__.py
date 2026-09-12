from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from cited_rag.evaluation.experiments import recommended_defaults, run_v1_matrix
from cited_rag.evaluation.run import persist_manifest, run_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run layered RAG evaluation")
    parser.add_argument("--dataset", default="evaluation/golden/v1.json")
    parser.add_argument("--out", default="evaluation/results/latest.json")
    parser.add_argument(
        "--matrix",
        action="store_true",
        help="Run dense-only, sparse-only, hybrid, and hybrid-rerank ablations",
    )
    args = parser.parse_args()
    if args.matrix:
        scores = asyncio.run(run_v1_matrix())
        out = Path(args.out)
        if out == Path("evaluation/results/latest.json"):
            out = Path("evaluation/results/matrix.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps([asdict(item) for item in scores], indent=2) + "\n",
            encoding="utf-8",
        )
        for item in scores:
            print(
                f"{item.name} recall@5={item.recall_at_5:.3f} mrr={item.mrr:.3f} "
                f"ndcg@5={item.ndcg_at_5:.3f} citation={item.citation_validity:.3f} "
                f"no_answer_p={item.no_answer_precision:.3f} "
                f"no_answer_r={item.no_answer_recall:.3f} "
                f"false_answer={item.false_answer_rate:.3f} "
                f"latency_ms={item.latency_ms} cases={item.cases}"
            )
        print(recommended_defaults(scores))
        print(f"wrote {out}")
        return
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
