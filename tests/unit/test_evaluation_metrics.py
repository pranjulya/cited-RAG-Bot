from __future__ import annotations

import math
from pathlib import Path
from uuid import uuid4

from cited_rag.evaluation.dataset import load_golden_dataset
from cited_rag.evaluation.metrics import (
    false_answer_rate,
    mrr,
    ndcg_at_k,
    no_answer_precision,
    no_answer_recall,
    recall_at_k,
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


def test_golden_dataset_loads() -> None:
    dataset = load_golden_dataset(Path("evaluation/golden/v1.json"))
    assert dataset.version == "golden-v1"
    assert {case.id for case in dataset.cases} == {"leave-policy", "unsupported-secret"}
    leave = next(case for case in dataset.cases if case.id == "leave-policy")
    assert leave.answerable is True
    secret = next(case for case in dataset.cases if case.id == "unsupported-secret")
    assert secret.answerable is False
