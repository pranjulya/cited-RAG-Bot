from __future__ import annotations

from uuid import UUID, uuid5

# Stable namespace so chunk UUIDv5 values are reproducible across processes.
CHUNK_ID_NAMESPACE = UUID("6b1e0c2a-9f3d-4c7e-8a12-7d3e5f1a2b0c")


def chunk_id_for(
    *,
    document_version_id: UUID,
    page_start: int,
    page_end: int,
    chunk_order: int,
    content_hash: str,
) -> UUID:
    name = f"{document_version_id}:{page_start}:{page_end}:{chunk_order}:{content_hash}"
    return uuid5(CHUNK_ID_NAMESPACE, name)
