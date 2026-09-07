from __future__ import annotations

from typing import Protocol

from cited_rag.domain.indexing import SparseVector
from cited_rag.domain.sparse import SparseEncoderConfig


class SparseEncoder(Protocol):
    config: SparseEncoderConfig

    async def encode_documents(self, texts: list[str]) -> list[SparseVector]: ...

    async def encode_query(self, text: str) -> SparseVector: ...
