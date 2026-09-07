from __future__ import annotations

from uuid import uuid4

import pytest

from cited_rag.adapters.chunking.page_window import PageWindowChunker
from cited_rag.application.chunking import persist_chunks
from cited_rag.domain.chunking import ChunkingConfig
from cited_rag.domain.exceptions import IngestionIntegrityError
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.document import DocumentVersion
from cited_rag.domain.models.page import Page


def _version(**kwargs: object) -> DocumentVersion:
    values: dict[str, object] = {
        "document_id": uuid4(),
        "collection_id": uuid4(),
        "version_number": 1,
        "content_hash": "h",
        "original_filename": "a.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 10,
        "storage_uri": "local://a.pdf",
    }
    values.update(kwargs)
    return DocumentVersion(**values)  # type: ignore[arg-type]


def _chunk(version: DocumentVersion) -> Chunk:
    return Chunk(
        collection_id=version.collection_id,
        document_id=version.document_id,
        document_version_id=version.id,
        page_start=1,
        page_end=1,
        chunk_order=0,
        text="hello",
        content_hash="abc",
    )


class _Chunks:
    def __init__(self, existing: list[Chunk]) -> None:
        self.existing = existing
        self.added: list[Chunk] = []

    async def list_by_version(self, _version_id: object) -> list[Chunk]:
        return self.existing

    async def add(self, chunk: Chunk) -> None:
        self.added.append(chunk)


class _Versions:
    def __init__(self) -> None:
        self.saved: dict[str, object] | None = None

    async def set_chunking_config(self, _version_id: object, config: dict[str, str | int]) -> None:
        self.saved = config


class _Uow:
    def __init__(self, chunks: _Chunks, versions: _Versions) -> None:
        self.chunks = chunks
        self.versions = versions


@pytest.mark.asyncio
async def test_existing_chunks_returned_only_when_config_matches() -> None:
    version = _version(
        chunking_config={"strategy": "page_char_split_v1", "target_chars": 40, "overlap_chars": 8}
    )
    existing = [_chunk(version)]
    uow = _Uow(_Chunks(existing), _Versions())
    chunker = PageWindowChunker(ChunkingConfig(target_chars=40, overlap_chars=8))
    pages = [Page(document_version_id=version.id, page_number=1, normalized_text="hello")]
    result = await persist_chunks(uow, version, pages, chunker)  # type: ignore[arg-type]
    assert result == existing
    assert uow.versions.saved is None
    assert uow.chunks.added == []


@pytest.mark.asyncio
async def test_existing_chunks_reject_missing_config() -> None:
    version = _version(chunking_config=None)
    uow = _Uow(_Chunks([_chunk(version)]), _Versions())
    chunker = PageWindowChunker(ChunkingConfig(target_chars=40, overlap_chars=8))
    with pytest.raises(IngestionIntegrityError, match="do not match"):
        await persist_chunks(uow, version, [], chunker)  # type: ignore[arg-type]
    assert uow.versions.saved is None


@pytest.mark.asyncio
async def test_existing_chunks_reject_different_config() -> None:
    version = _version(
        chunking_config={"strategy": "page_char_split_v1", "target_chars": 40, "overlap_chars": 8}
    )
    uow = _Uow(_Chunks([_chunk(version)]), _Versions())
    chunker = PageWindowChunker(ChunkingConfig(target_chars=1200, overlap_chars=200))
    with pytest.raises(IngestionIntegrityError, match="do not match"):
        await persist_chunks(uow, version, [], chunker)  # type: ignore[arg-type]
    assert uow.versions.saved is None
