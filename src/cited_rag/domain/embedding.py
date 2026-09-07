from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    """Evaluation-tunable dense embedding. Model names stay configuration."""

    dimension: int = 32
    batch_size: int = 32
    model: str = "hash-v1"
    index_version: str = "v1"

    def __post_init__(self) -> None:
        if self.dimension < 1:
            raise ValueError("embedding dimension must be >= 1")
        if self.batch_size < 1:
            raise ValueError("embedding batch_size must be >= 1")
        if not self.index_version.strip():
            raise ValueError("index_version must be non-empty")
