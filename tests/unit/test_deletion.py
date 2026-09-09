from __future__ import annotations

from uuid import uuid4

import pytest

from cited_rag.adapters.embedding.hashing import HashEmbeddingProvider
from cited_rag.adapters.queue.memory import MemoryJobQueue
from cited_rag.adapters.retrieval.memory import MemoryRetrievalStore
from cited_rag.application.deletion import tombstone_document
from cited_rag.application.indexing import persist_dense_index
from cited_rag.domain.clock import utc_now
from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.enums import DocumentVersionStatus
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.document import Document, DocumentVersion


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


def _chunk(version: DocumentVersion, order: int, text: str) -> Chunk:
    return Chunk(
        collection_id=version.collection_id,
        document_id=version.document_id,
        document_version_id=version.id,
        page_start=1,
        page_end=1,
        chunk_order=order,
        text=text,
        content_hash=f"h{order}",
    )


@pytest.mark.asyncio
async def test_delete_version_points_leaves_other_versions() -> None:
    keep = _version()
    drop = _version()
    store = MemoryRetrievalStore()
    config = EmbeddingConfig(dimension=8, batch_size=8)
    await persist_dense_index(
        [_chunk(keep, 0, "keep me"), _chunk(drop, 0, "drop me")],
        embedder=HashEmbeddingProvider(dimension=8),
        store=store,
        config=config,
    )
    assert len(store.points) == 2
    await store.delete_version_points(drop.id)
    remaining = list(store.points.values())
    assert len(remaining) == 1
    assert remaining[0].payload["document_version_id"] == str(keep.id)


@pytest.mark.asyncio
async def test_delete_version_points_is_idempotent() -> None:
    version = _version()
    store = MemoryRetrievalStore()
    await persist_dense_index(
        [_chunk(version, 0, "gone")],
        embedder=HashEmbeddingProvider(dimension=8),
        store=store,
        config=EmbeddingConfig(dimension=8),
    )
    await store.delete_version_points(version.id)
    await store.delete_version_points(version.id)
    assert store.points == {}


class _Documents:
    def __init__(self, document: Document) -> None:
        self.document = document

    async def get(self, _document_id: object) -> Document:
        return self.document

    async def mark_deleted(self, _document_id: object) -> None:
        object.__setattr__(self.document, "deleted_at", utc_now())


class _Versions:
    def __init__(self, versions: list[DocumentVersion]) -> None:
        self.versions = versions

    async def list_by_document(self, _document_id: object) -> list[DocumentVersion]:
        return self.versions

    async def transition(self, version_id: object, _from: object, to: object) -> DocumentVersion:
        for version in self.versions:
            if version.id == version_id:
                object.__setattr__(version, "ingestion_status", to)
                return version
        raise AssertionError("missing version")

    async def mark_deleting(self, version_id: object) -> None:
        await self.transition(version_id, None, DocumentVersionStatus.DELETING)


class _Uow:
    def __init__(self, documents: _Documents, versions: _Versions) -> None:
        self.documents = documents
        self.versions = versions
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


@pytest.mark.asyncio
async def test_repeat_delete_re_enqueues_cleanup() -> None:
    document = Document(collection_id=uuid4(), logical_name="gone", deleted_at=utc_now())
    queue = MemoryJobQueue()
    uow = _Uow(_Documents(document), _Versions([]))
    await tombstone_document(uow, queue, document_id=document.id)
    assert queue.cleanup_jobs == [(document.id, None)]
    await tombstone_document(uow, queue, document_id=document.id)
    assert len(queue.cleanup_jobs) == 2
