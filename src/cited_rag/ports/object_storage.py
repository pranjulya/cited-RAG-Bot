from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID


def source_pdf_key(*, collection_id: UUID, document_id: UUID, version_id: UUID) -> str:
    return f"collections/{collection_id}/documents/{document_id}/versions/{version_id}/source.pdf"


def key_from_storage_uri(uri: str) -> str:
    prefix = "local://"
    if uri.startswith(prefix):
        key = uri[len(prefix) :]
        if key:
            return key
    raise ValueError("unsupported or empty storage uri")


class ObjectStorage(Protocol):
    async def put(self, key: str, chunks: AsyncIterator[bytes]) -> str:
        """Persist bytes at key. Returns a durable storage URI."""

    async def get(self, key: str) -> bytes:
        """Return object bytes. Used for compensation checks and reprocess."""

    async def delete(self, key: str) -> None:
        """Delete the object if it exists. Missing keys are not an error."""
