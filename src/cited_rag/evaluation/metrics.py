from __future__ import annotations

import math
from collections.abc import Sequence
from uuid import UUID


def recall_at_k(retrieved: Sequence[UUID], relevant: set[UUID], k: int) -> float:
    if k < 1:
        return 0.0
    if not relevant:
        return 1.0
    hits = sum(1 for item in retrieved[:k] if item in relevant)
    return hits / len(relevant)


def mrr(retrieved: Sequence[UUID], relevant: set[UUID]) -> float:
    if not relevant:
        return 0.0
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved: Sequence[UUID], relevant: set[UUID], k: int) -> float:
    if k < 1 or not relevant:
        return 0.0 if relevant else 1.0
    dcg = 0.0
    for rank, item in enumerate(retrieved[:k], start=1):
        if item in relevant:
            dcg += 1.0 / math.log2(rank + 1)
    ideal_hits = min(k, len(relevant))
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return 0.0 if idcg == 0 else dcg / idcg


def no_answer_precision(abstained: int, abstained_correct: int) -> float:
    if abstained == 0:
        return 1.0
    return abstained_correct / abstained


def no_answer_recall(unanswerable: int, abstained_correct: int) -> float:
    if unanswerable == 0:
        return 1.0
    return abstained_correct / unanswerable


def false_answer_rate(unanswerable: int, answered_unanswerable: int) -> float:
    if unanswerable == 0:
        return 0.0
    return answered_unanswerable / unanswerable
