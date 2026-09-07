from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from cited_rag.adapters.storage.local import LocalObjectStorage
from cited_rag.domain.exceptions import StorageError
from cited_rag.ports.object_storage import key_from_storage_uri, source_pdf_key


async def _chunks(*parts: bytes) -> AsyncIterator[bytes]:
    for part in parts:
        yield part


@pytest.mark.asyncio
async def test_put_get_delete_round_trip(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path)
    key = "collections/c/documents/d/versions/v/source.pdf"
    uri = await storage.put(key, _chunks(b"%PDF", b"-1.4"))
    assert uri == f"local://{key}"
    assert await storage.get(key) == b"%PDF-1.4"
    await storage.delete(key)
    with pytest.raises(StorageError):
        await storage.get(key)


def test_source_pdf_key_layout() -> None:
    from uuid import UUID

    key = source_pdf_key(
        collection_id=UUID("11111111-1111-1111-1111-111111111111"),
        document_id=UUID("22222222-2222-2222-2222-222222222222"),
        version_id=UUID("33333333-3333-3333-3333-333333333333"),
    )
    assert key == (
        "collections/11111111-1111-1111-1111-111111111111/"
        "documents/22222222-2222-2222-2222-222222222222/"
        "versions/33333333-3333-3333-3333-333333333333/source.pdf"
    )


def test_key_from_local_storage_uri() -> None:
    key = (
        "collections/11111111-1111-1111-1111-111111111111/"
        "documents/22222222-2222-2222-2222-222222222222/"
        "versions/33333333-3333-3333-3333-333333333333/source.pdf"
    )
    assert key_from_storage_uri(f"local://{key}") == key
    with pytest.raises(ValueError):
        key_from_storage_uri("s3://bucket/key")
