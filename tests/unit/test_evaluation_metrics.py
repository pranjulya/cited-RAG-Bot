from __future__ import annotations

import json
import math
from pathlib import Path
from uuid import uuid4

import pytest

from cited_rag.domain.models.decision import EvidenceDecision
from cited_rag.evaluation.dataset import load_golden_dataset
from cited_rag.evaluation.metrics import (
    false_answer_rate,
    mrr,
    ndcg_at_k,
    no_answer_precision,
    no_answer_recall,
    recall_at_k,
)


class _FakeDecisioner:
    async def decide(self, question: str, evidence: object) -> EvidenceDecision:
        del evidence
        return EvidenceDecision(
            answerable_probability=0.9 if "leave" in question else 0.1,
            model="fake-jev",
        )


def test_recall_mrr_ndcg_hand_calculated() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    retrieved = [a, c, b]
    relevant = {a, b}
    assert recall_at_k(retrieved, relevant, 2) == 0.5
    assert mrr(retrieved, relevant) == 1.0
    dcg = 1.0 / math.log2(2) + 1.0 / math.log2(4)
    idcg = 1.0 / math.log2(2) + 1.0 / math.log2(3)
    assert ndcg_at_k(retrieved, relevant, 3) == dcg / idcg


def test_ndcg_uses_log2_ranks() -> None:
    a, b = uuid4(), uuid4()
    relevant = {a}
    assert ndcg_at_k([a, b], relevant, 2) == 1.0
    assert ndcg_at_k([b, a], relevant, 2) == (1.0 / math.log2(3))


def test_no_answer_metrics() -> None:
    assert no_answer_precision(abstained=2, abstained_correct=2) == 1.0
    assert no_answer_recall(unanswerable=2, abstained_correct=1) == 0.5
    assert false_answer_rate(unanswerable=2, answered_unanswerable=1) == 0.5


@pytest.mark.asyncio
async def test_evaluation_command_writes_layer_results(tmp_path: Path) -> None:
    from cited_rag.evaluation.run import persist_manifest, run_evaluation

    manifest = await run_evaluation(Path("evaluation/golden/v1.json"))
    out = tmp_path / "latest.json"
    persist_manifest(manifest, out)
    assert manifest.layers.cases == 2
    assert 0.0 <= manifest.layers.recall_at_5 <= 1.0
    assert out.is_file()
    assert "recall_at_5" in out.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_evaluation_can_compare_opt_in_shadow_decisions() -> None:
    from cited_rag.evaluation.run import run_evaluation

    manifest = await run_evaluation(
        Path("evaluation/golden/v1.json"),
        decisioner=_FakeDecisioner(),
    )

    assert manifest.jev_shadow is not None
    assert manifest.jev_shadow.cases == 2
    assert manifest.jev_shadow.failures == 0
    assert manifest.jev_shadow.agreement == 1.0
    assert set(manifest.jev_shadow.probabilities) == {"leave-policy", "unsupported-secret"}


def test_evaluation_matrix_cli_writes_ablations(tmp_path: Path, monkeypatch) -> None:
    from cited_rag.evaluation.__main__ import main

    out = tmp_path / "matrix.json"
    monkeypatch.setattr(
        "sys.argv",
        ["cited_rag.evaluation", "--matrix", "--out", str(out)],
    )
    main()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert [row["name"] for row in payload] == [
        "dense-only",
        "sparse-only",
        "hybrid",
        "hybrid-rerank",
    ]
    assert all("recall_at_5" in row and "mrr" in row for row in payload)


def test_golden_dataset_loads() -> None:
    dataset = load_golden_dataset(Path("evaluation/golden/v1.json"))
    assert dataset.version == "golden-v1"
    assert {case.id for case in dataset.cases} == {"leave-policy", "unsupported-secret"}
    leave = next(case for case in dataset.cases if case.id == "leave-policy")
    assert leave.answerable is True
    secret = next(case for case in dataset.cases if case.id == "unsupported-secret")
    assert secret.answerable is False
