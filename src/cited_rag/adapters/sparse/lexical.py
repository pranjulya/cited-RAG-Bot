from __future__ import annotations

import hashlib
import re
from collections import Counter

from cited_rag.domain.exceptions import PermanentIngestionError
from cited_rag.domain.indexing import SparseVector
from cited_rag.domain.sparse import SparseEncoderConfig

_TOKEN = re.compile(r"[A-Za-z0-9_]+")


def _index_for(token: str) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).digest()[:4]
    return int.from_bytes(digest, "big") % 2_147_483_647


def _encode(text: str) -> SparseVector:
    counts = Counter(token.lower() for token in _TOKEN.findall(text))
    items = sorted((_index_for(token), float(tf)) for token, tf in counts.items())
    merged: dict[int, float] = {}
    for index, value in items:
        merged[index] = merged.get(index, 0.0) + value
    indices = sorted(merged)
    return SparseVector(indices=indices, values=[merged[index] for index in indices])


class LexicalSparseEncoder:
    """Deterministic bag-of-tokens sparse vectors for tests/dev. Not BM42."""

    def __init__(self, config: SparseEncoderConfig | None = None) -> None:
        self.config = config or SparseEncoderConfig()

    async def encode_documents(self, texts: list[str]) -> list[SparseVector]:
        if not texts:
            raise PermanentIngestionError(
                "sparse encoding batch is empty",
                failure_code="SPARSE_INDEX_FAILED",
            )
        return [_encode(text) for text in texts]

    async def encode_query(self, text: str) -> SparseVector:
        vectors = await self.encode_documents([text])
        return vectors[0]
