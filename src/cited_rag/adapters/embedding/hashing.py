from __future__ import annotations

import hashlib
import math

from cited_rag.domain.exceptions import PermanentIngestionError


def _vector(text: str, dimension: int) -> list[float]:
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < dimension:
        for byte in seed:
            values.append((byte / 127.5) - 1.0)
            if len(values) == dimension:
                break
        seed = hashlib.sha256(seed).digest()
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


class HashEmbeddingProvider:
    """Deterministic dense vectors for tests and local development. Not a semantic model."""

    name = "hash"

    def __init__(self, *, dimension: int) -> None:
        if dimension < 1:
            raise ValueError("embedding dimension must be >= 1")
        self.dimension = dimension

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            raise PermanentIngestionError(
                "embedding batch is empty",
                failure_code="EMBEDDING_FAILED",
            )
        return [_vector(text, self.dimension) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_documents([text])
        return vectors[0]
