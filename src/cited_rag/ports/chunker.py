from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from cited_rag.domain.chunking import ChunkingConfig
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.document import DocumentVersion
from cited_rag.domain.models.page import Page


class Chunker(Protocol):
    config: ChunkingConfig

    def chunk(self, version: DocumentVersion, pages: Sequence[Page]) -> list[Chunk]: ...
