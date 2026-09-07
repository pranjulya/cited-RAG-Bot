from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    """Evaluation-tunable splitter. V1 prefers single-page windows."""

    strategy: str = "page_char_split_v1"
    target_chars: int = 1200
    overlap_chars: int = 200

    def __post_init__(self) -> None:
        if self.target_chars < 1:
            raise ValueError("chunk target_chars must be >= 1")
        if self.overlap_chars < 0:
            raise ValueError("chunk overlap_chars must be >= 0")
        if self.overlap_chars >= self.target_chars:
            raise ValueError("chunk overlap_chars must be smaller than target_chars")

    def as_record(self) -> dict[str, str | int]:
        return {
            "strategy": self.strategy,
            "target_chars": self.target_chars,
            "overlap_chars": self.overlap_chars,
        }
