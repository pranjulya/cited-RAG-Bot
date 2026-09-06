from __future__ import annotations

from uuid import UUID, uuid4

from cited_rag.domain.ids import chunk_id_for


def test_chunk_id_is_deterministic_uuidv5() -> None:
    version_id = UUID("11111111-1111-1111-1111-111111111111")
    first = chunk_id_for(
        document_version_id=version_id,
        page_start=2,
        page_end=2,
        chunk_order=0,
        content_hash="abc",
    )
    second = chunk_id_for(
        document_version_id=version_id,
        page_start=2,
        page_end=2,
        chunk_order=0,
        content_hash="abc",
    )
    assert first == second
    assert first.version == 5


def test_chunk_id_changes_when_provenance_changes() -> None:
    version_id = uuid4()
    base = chunk_id_for(
        document_version_id=version_id,
        page_start=1,
        page_end=1,
        chunk_order=0,
        content_hash="abc",
    )
    different_page = chunk_id_for(
        document_version_id=version_id,
        page_start=2,
        page_end=2,
        chunk_order=0,
        content_hash="abc",
    )
    different_order = chunk_id_for(
        document_version_id=version_id,
        page_start=1,
        page_end=1,
        chunk_order=1,
        content_hash="abc",
    )
    assert base != different_page
    assert base != different_order
