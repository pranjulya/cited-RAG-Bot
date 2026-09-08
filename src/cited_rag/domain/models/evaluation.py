from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvaluationRunConfig:
    """Ablation flags for evaluation only. Not a production query fallback."""

    include_dense: bool = True
    include_sparse: bool = True
