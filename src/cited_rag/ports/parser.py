from __future__ import annotations

from typing import BinaryIO, Protocol

from cited_rag.domain.parser import ParsedPage


class DocumentParser(Protocol):
    """Provider-neutral page-aware PDF parser. Implementations must not leak SDK types."""

    name: str

    async def parse(self, source: BinaryIO) -> list[ParsedPage]: ...
