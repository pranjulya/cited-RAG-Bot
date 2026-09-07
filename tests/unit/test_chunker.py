from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from cited_rag.adapters.chunking.page_window import PageWindowChunker
from cited_rag.domain.chunking import ChunkingConfig
from cited_rag.domain.models.document import DocumentVersion
from cited_rag.domain.models.page import Page


def _version() -> DocumentVersion:
    return DocumentVersion(
        document_id=uuid4(),
        collection_id=uuid4(),
        version_number=1,
        content_hash="h",
        original_filename="a.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        storage_uri="local://a.pdf",
    )


def _page(version_id: UUID, number: int, text: str) -> Page:
    return Page(
        document_version_id=version_id,
        page_number=number,
        raw_text=text,
        normalized_text=text,
    )


def test_short_page_is_one_chunk() -> None:
    version = _version()
    chunker = PageWindowChunker(ChunkingConfig(target_chars=100, overlap_chars=20))
    chunks = chunker.chunk(version, [_page(version.id, 1, "hello world")])
    assert len(chunks) == 1
    assert chunks[0].page_start == chunks[0].page_end == 1
    assert chunks[0].chunk_order == 0
    assert chunks[0].text == "hello world"
    assert chunks[0].id.version == 5


def test_multi_page_keeps_page_identity_and_order() -> None:
    version = _version()
    chunker = PageWindowChunker()
    chunks = chunker.chunk(
        version,
        [
            _page(version.id, 2, "second"),
            _page(version.id, 1, "first"),
        ],
    )
    assert [c.chunk_order for c in chunks] == [0, 1]
    assert chunks[0].page_start == 1 and chunks[0].text == "first"
    assert chunks[1].page_start == 2 and chunks[1].text == "second"


def test_long_page_splits_with_overlap() -> None:
    version = _version()
    # Unique digit pairs so a suffix/prefix match cannot be accidental.
    text = "".join(f"{index:02d}" for index in range(40))
    overlap = 8
    chunker = PageWindowChunker(ChunkingConfig(target_chars=20, overlap_chars=overlap))
    chunks = chunker.chunk(version, [_page(version.id, 1, text)])
    assert len(chunks) >= 2
    assert all(c.page_start == 1 and c.page_end == 1 for c in chunks)
    assert all(c.text in text for c in chunks)
    assert [c.chunk_order for c in chunks] == list(range(len(chunks)))
    assert chunks[0].text != chunks[1].text
    assert chunks[0].text[-overlap:] == chunks[1].text[:overlap]
    assert text.startswith(chunks[0].text)


def test_empty_pages_are_skipped() -> None:
    version = _version()
    chunker = PageWindowChunker()
    chunks = chunker.chunk(
        version,
        [_page(version.id, 1, ""), _page(version.id, 2, "kept")],
    )
    assert len(chunks) == 1
    assert chunks[0].page_start == 2


def test_ids_are_deterministic() -> None:
    version = _version()
    pages = [_page(version.id, 1, "same text")]
    chunker = PageWindowChunker()
    first = chunker.chunk(version, pages)
    second = chunker.chunk(version, pages)
    assert [c.id for c in first] == [c.id for c in second]


def test_config_record_is_reproducible() -> None:
    record = ChunkingConfig(target_chars=80, overlap_chars=16).as_record()
    assert record == {
        "strategy": "page_char_split_v1",
        "target_chars": 80,
        "overlap_chars": 16,
    }


def test_invalid_overlap_rejected() -> None:
    with pytest.raises(ValueError, match="overlap"):
        ChunkingConfig(target_chars=100, overlap_chars=100)
