from __future__ import annotations

import logging
from collections.abc import Sequence

from cited_rag.domain.exceptions import PermanentIngestionError
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.document import DocumentVersion
from cited_rag.domain.models.page import Page
from cited_rag.ports.chunker import Chunker
from cited_rag.ports.repositories import UnitOfWork

logger = logging.getLogger("cited_rag.chunking")


async def persist_chunks(
    uow: UnitOfWork,
    version: DocumentVersion,
    pages: Sequence[Page],
    chunker: Chunker,
) -> list[Chunk]:
    """Persist provenance-aware chunks. Never marks READY."""
    existing = await uow.chunks.list_by_version(version.id)
    if existing:
        logger.info(
            "chunks already persisted count=%s",
            len(existing),
            extra={"correlation_id": "-"},
        )
        return existing

    chunks = chunker.chunk(version, pages)
    if not chunks:
        raise PermanentIngestionError(
            "no chunks produced from parsed pages",
            failure_code="PDF_UNSUPPORTED",
        )
    for chunk in chunks:
        await uow.chunks.add(chunk)
    logger.info(
        "chunked count=%s strategy=%s target=%s overlap=%s",
        len(chunks),
        chunker.config.strategy,
        chunker.config.target_chars,
        chunker.config.overlap_chars,
        extra={"correlation_id": "-"},
    )
    return chunks
