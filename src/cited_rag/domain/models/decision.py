from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvidenceDecision:
    """Normalized, provider-independent shadow answerability result."""

    answerable_probability: float
    model: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.answerable_probability) or not (
            0 <= self.answerable_probability <= 1
        ):
            raise ValueError("answerable probability must be between 0 and 1")
        if not self.model.strip():
            raise ValueError("decision model must not be empty")

    @property
    def answerable(self) -> bool:
        return self.answerable_probability >= 0.5
