from __future__ import annotations

import pytest

from cited_rag.evaluation.experiments import recommended_defaults, run_v1_matrix


@pytest.mark.asyncio
async def test_experiment_matrix_is_reproducible() -> None:
    first = await run_v1_matrix()
    second = await run_v1_matrix()
    assert [item.name for item in first] == ["dense-only", "sparse-only", "hybrid", "hybrid-rerank"]
    assert [(a.name, a.recall_at_5, a.mrr) for a in first] == [
        (b.name, b.recall_at_5, b.mrr) for b in second
    ]
    assert all(item.cases == 2 for item in first)
    assert all(0.0 <= item.recall_at_5 <= 1.0 for item in first)


def test_recommended_defaults_keep_hybrid_rerank() -> None:
    text = recommended_defaults()
    assert "hybrid" in text
    assert "rerank" in text
