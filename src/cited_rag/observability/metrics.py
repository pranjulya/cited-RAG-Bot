from __future__ import annotations

from collections import Counter


class InMemoryMetrics:
    """Process-local counters. High-cardinality IDs stay in logs, not labels."""

    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()

    def incr(self, name: str, amount: int = 1) -> None:
        self._counts[name] += amount

    def get(self, name: str) -> int:
        return int(self._counts.get(name, 0))

    def snapshot(self) -> dict[str, int]:
        return dict(self._counts)


metrics = InMemoryMetrics()
