from __future__ import annotations

from cited_rag.adapters.chunking.page_window import PageWindowChunker
from cited_rag.config import Settings
from cited_rag.domain.chunking import ChunkingConfig
from cited_rag.ports.chunker import Chunker


def create_chunker(settings: Settings) -> Chunker:
    return PageWindowChunker(
        ChunkingConfig(
            target_chars=settings.chunk_target_chars,
            overlap_chars=settings.chunk_overlap_chars,
        )
    )
