from __future__ import annotations

import hashlib
from collections.abc import Sequence

from cited_rag.domain.chunking import ChunkingConfig
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.document import DocumentVersion
from cited_rag.domain.models.page import Page


def _page_text(page: Page) -> str:
    text = page.normalized_text if page.normalized_text is not None else page.raw_text
    return (text or "").strip()


def _windows(text: str, *, target: int, overlap: int) -> list[str]:
    if len(text) <= target:
        return [text]
    pieces: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + target, length)
        if end < length:
            window = text[start:end]
            break_at = max(window.rfind("\n"), window.rfind(" "))
            # A window shorter than overlap would make next_start <= start and
            # drop overlap. Keep the hard target unless the break leaves room.
            if break_at > overlap:
                end = start + break_at
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= length:
            break
        next_start = end - overlap
        if next_start <= start:
            next_start = end
        start = next_start
    return pieces


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class PageWindowChunker:
    """Split within a page. Never silently merges unrelated pages."""

    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self.config = config or ChunkingConfig()

    def chunk(self, version: DocumentVersion, pages: Sequence[Page]) -> list[Chunk]:
        ordered = sorted(pages, key=lambda page: page.page_number)
        chunks: list[Chunk] = []
        order = 0
        for page in ordered:
            text = _page_text(page)
            if not text:
                continue
            for piece in _windows(
                text,
                target=self.config.target_chars,
                overlap=self.config.overlap_chars,
            ):
                chunks.append(
                    Chunk(
                        collection_id=version.collection_id,
                        document_id=version.document_id,
                        document_version_id=version.id,
                        page_start=page.page_number,
                        page_end=page.page_number,
                        chunk_order=order,
                        text=piece,
                        content_hash=_content_hash(piece),
                        token_count=len(piece.split()),
                    )
                )
                order += 1
        return chunks
