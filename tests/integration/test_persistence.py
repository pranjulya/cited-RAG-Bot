from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from cited_rag.adapters.persistence.postgres.uow import PostgresUnitOfWork
from cited_rag.domain.enums import (
    DocumentVersionStatus,
    IngestionJobStatus,
    QueryRunStatus,
)
from cited_rag.domain.exceptions import (
    DuplicateContentHashError,
    DuplicateIdentityError,
    InvalidLifecycleTransitionError,
)
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.collection import Collection
from cited_rag.domain.models.document import Document, DocumentVersion
from cited_rag.domain.models.ingestion import IngestionJob
from cited_rag.domain.models.page import Page
from cited_rag.domain.models.principal import ApiPrincipal
from cited_rag.domain.models.query import QueryRun

pytestmark = pytest.mark.postgres


def _uow(session_factory: async_sessionmaker) -> PostgresUnitOfWork:
    return PostgresUnitOfWork(session_factory)


async def _principal_and_collection(
    session_factory: async_sessionmaker,
) -> tuple[ApiPrincipal, Collection]:
    principal = ApiPrincipal(name="test-owner")
    collection = Collection(name="handbook", owner_id=principal.id)
    async with _uow(session_factory) as uow:
        await uow.principals.add(principal)
        await uow.collections.add(collection)
        await uow.commit()
    return principal, collection


@pytest.mark.asyncio
async def test_create_and_read_collection(uow_factory: async_sessionmaker) -> None:
    principal, collection = await _principal_and_collection(uow_factory)
    async with _uow(uow_factory) as uow:
        loaded = await uow.collections.get(collection.id)
        owner = await uow.principals.get(principal.id)
    assert loaded is not None
    assert loaded.name == "handbook"
    assert loaded.owner_id == principal.id
    assert owner is not None
    assert owner.name == "test-owner"


@pytest.mark.asyncio
async def test_document_belongs_to_collection(uow_factory: async_sessionmaker) -> None:
    _, collection = await _principal_and_collection(uow_factory)
    document = Document(collection_id=collection.id, logical_name="policy.pdf")
    async with _uow(uow_factory) as uow:
        await uow.documents.add(document)
        await uow.commit()
    async with _uow(uow_factory) as uow:
        loaded = await uow.documents.get(document.id)
    assert loaded is not None
    assert loaded.collection_id == collection.id
    assert loaded.logical_name == "policy.pdf"
    assert loaded.active_version_id is None


@pytest.mark.asyncio
async def test_document_version_lifecycle_persistence(
    uow_factory: async_sessionmaker,
) -> None:
    _, collection = await _principal_and_collection(uow_factory)
    document = Document(collection_id=collection.id, logical_name="policy.pdf")
    version = DocumentVersion(
        document_id=document.id,
        collection_id=collection.id,
        version_number=1,
        content_hash="hash-1",
        original_filename="policy.pdf",
        mime_type="application/pdf",
        size_bytes=12,
        storage_uri="local://policy.pdf",
    )
    async with _uow(uow_factory) as uow:
        await uow.documents.add(document)
        await uow.versions.add(version)
        await uow.commit()

    async with _uow(uow_factory) as uow:
        await uow.versions.transition(
            version.id, DocumentVersionStatus.UPLOADED, DocumentVersionStatus.QUEUED
        )
        await uow.versions.transition(
            version.id, DocumentVersionStatus.QUEUED, DocumentVersionStatus.PROCESSING
        )
        ready = await uow.versions.transition(
            version.id, DocumentVersionStatus.PROCESSING, DocumentVersionStatus.READY
        )
        await uow.documents.set_active_version(document.id, version.id)
        await uow.commit()

    async with _uow(uow_factory) as uow:
        loaded = await uow.versions.get(version.id)
        doc = await uow.documents.get(document.id)
    assert loaded is not None
    assert loaded.ingestion_status is DocumentVersionStatus.READY
    assert loaded.ready_at is not None
    assert ready.ready_at is not None
    assert doc is not None
    assert doc.active_version_id == version.id


@pytest.mark.asyncio
async def test_page_and_chunk_provenance_survives_round_trip(
    uow_factory: async_sessionmaker,
) -> None:
    _, collection = await _principal_and_collection(uow_factory)
    document = Document(collection_id=collection.id, logical_name="policy.pdf")
    version = DocumentVersion(
        document_id=document.id,
        collection_id=collection.id,
        version_number=1,
        content_hash="hash-2",
        original_filename="policy.pdf",
        mime_type="application/pdf",
        size_bytes=12,
        storage_uri="local://policy.pdf",
    )
    page = Page(
        document_version_id=version.id,
        page_number=1,
        raw_text="raw",
        normalized_text="normalized",
        extraction_metadata={"parser": "test"},
    )
    chunk = Chunk(
        collection_id=collection.id,
        document_id=document.id,
        document_version_id=version.id,
        page_start=1,
        page_end=1,
        chunk_order=0,
        text="normalized",
        content_hash="chunk-hash",
        token_count=2,
    )
    job = IngestionJob(
        document_version_id=version.id,
        status=IngestionJobStatus.PENDING,
        correlation_id="corr-1",
    )
    async with _uow(uow_factory) as uow:
        await uow.documents.add(document)
        await uow.versions.add(version)
        await uow.pages.add(page)
        await uow.chunks.add(chunk)
        await uow.ingestion_jobs.add(job)
        await uow.commit()

    async with _uow(uow_factory) as uow:
        pages = await uow.pages.list_by_version(version.id)
        chunks = await uow.chunks.list_by_version(version.id)
        loaded_chunk = await uow.chunks.get(chunk.id)
        loaded_job = await uow.ingestion_jobs.get_by_version(version.id)

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].normalized_text == "normalized"
    assert pages[0].extraction_metadata == {"parser": "test"}
    assert len(chunks) == 1
    assert loaded_chunk is not None
    assert loaded_chunk.id == chunk.id
    assert loaded_chunk.collection_id == collection.id
    assert loaded_chunk.document_id == document.id
    assert loaded_chunk.document_version_id == version.id
    assert loaded_chunk.page_start == 1
    assert loaded_chunk.text == "normalized"
    assert loaded_job is not None
    assert loaded_job.correlation_id == "corr-1"


@pytest.mark.asyncio
async def test_duplicate_identifiers_rejected(uow_factory: async_sessionmaker) -> None:
    principal = ApiPrincipal(name="dup-owner")
    async with _uow(uow_factory) as uow:
        await uow.principals.add(principal)
        await uow.commit()
    with pytest.raises(DuplicateIdentityError):
        async with _uow(uow_factory) as uow:
            await uow.principals.add(principal)


@pytest.mark.asyncio
async def test_duplicate_content_hash_rejected_within_collection(
    uow_factory: async_sessionmaker,
) -> None:
    _, collection = await _principal_and_collection(uow_factory)
    first_doc = Document(collection_id=collection.id, logical_name="a.pdf")
    second_doc = Document(collection_id=collection.id, logical_name="b.pdf")
    shared_hash = "same-bytes"
    v1 = DocumentVersion(
        document_id=first_doc.id,
        collection_id=collection.id,
        version_number=1,
        content_hash=shared_hash,
        original_filename="a.pdf",
        mime_type="application/pdf",
        size_bytes=1,
        storage_uri="local://a.pdf",
    )
    v2 = DocumentVersion(
        document_id=second_doc.id,
        collection_id=collection.id,
        version_number=1,
        content_hash=shared_hash,
        original_filename="b.pdf",
        mime_type="application/pdf",
        size_bytes=1,
        storage_uri="local://b.pdf",
    )
    async with _uow(uow_factory) as uow:
        await uow.documents.add(first_doc)
        await uow.versions.add(v1)
        await uow.documents.add(second_doc)
        await uow.commit()
    with pytest.raises(DuplicateContentHashError):
        async with _uow(uow_factory) as uow:
            await uow.versions.add(v2)


@pytest.mark.asyncio
async def test_same_content_hash_allowed_in_different_collections(
    uow_factory: async_sessionmaker,
) -> None:
    principal, collection_a = await _principal_and_collection(uow_factory)
    collection_b = Collection(name="other", owner_id=principal.id)
    async with _uow(uow_factory) as uow:
        await uow.collections.add(collection_b)
        await uow.commit()
    shared_hash = "cross-collection-hash"
    doc_a = Document(collection_id=collection_a.id, logical_name="a.pdf")
    doc_b = Document(collection_id=collection_b.id, logical_name="a.pdf")
    async with _uow(uow_factory) as uow:
        await uow.documents.add(doc_a)
        await uow.versions.add(
            DocumentVersion(
                document_id=doc_a.id,
                collection_id=collection_a.id,
                version_number=1,
                content_hash=shared_hash,
                original_filename="a.pdf",
                mime_type="application/pdf",
                size_bytes=1,
                storage_uri="local://a.pdf",
            )
        )
        await uow.documents.add(doc_b)
        await uow.versions.add(
            DocumentVersion(
                document_id=doc_b.id,
                collection_id=collection_b.id,
                version_number=1,
                content_hash=shared_hash,
                original_filename="a.pdf",
                mime_type="application/pdf",
                size_bytes=1,
                storage_uri="local://a.pdf",
            )
        )
        await uow.commit()


@pytest.mark.asyncio
async def test_rollback_leaves_no_partial_state(uow_factory: async_sessionmaker) -> None:
    principal = ApiPrincipal(name="rollback-owner")
    collection = Collection(name="rollback", owner_id=principal.id)
    document = Document(collection_id=collection.id, logical_name="gone.pdf")
    with pytest.raises(RuntimeError, match="boom"):
        async with _uow(uow_factory) as uow:
            await uow.principals.add(principal)
            await uow.collections.add(collection)
            await uow.documents.add(document)
            raise RuntimeError("boom")

    async with _uow(uow_factory) as uow:
        assert await uow.principals.get(principal.id) is None
        assert await uow.collections.get(collection.id) is None
        assert await uow.documents.get(document.id) is None


@pytest.mark.asyncio
async def test_invalid_lifecycle_transition_does_not_change_status(
    uow_factory: async_sessionmaker,
) -> None:
    _, collection = await _principal_and_collection(uow_factory)
    document = Document(collection_id=collection.id, logical_name="policy.pdf")
    version = DocumentVersion(
        document_id=document.id,
        collection_id=collection.id,
        version_number=1,
        content_hash="hash-invalid-transition",
        original_filename="policy.pdf",
        mime_type="application/pdf",
        size_bytes=1,
        storage_uri="local://policy.pdf",
    )
    async with _uow(uow_factory) as uow:
        await uow.documents.add(document)
        await uow.versions.add(version)
        await uow.commit()
    with pytest.raises(InvalidLifecycleTransitionError):
        async with _uow(uow_factory) as uow:
            await uow.versions.transition(
                version.id, DocumentVersionStatus.UPLOADED, DocumentVersionStatus.READY
            )
    async with _uow(uow_factory) as uow:
        loaded = await uow.versions.get(version.id)
    assert loaded is not None
    assert loaded.ingestion_status is DocumentVersionStatus.UPLOADED


@pytest.mark.asyncio
async def test_query_run_audit_round_trip(uow_factory: async_sessionmaker) -> None:
    principal, collection = await _principal_and_collection(uow_factory)
    query_run = QueryRun(
        collection_id=collection.id,
        principal_id=principal.id,
        question="What is the policy?",
        status=QueryRunStatus.STARTED,
        correlation_id="q-1",
    )
    async with _uow(uow_factory) as uow:
        await uow.query_runs.add(query_run)
        await uow.commit()
    async with _uow(uow_factory) as uow:
        loaded = await uow.query_runs.get(query_run.id)
    assert loaded is not None
    assert loaded.collection_id == collection.id
    assert loaded.question == "What is the policy?"
    assert loaded.correlation_id == "q-1"


@pytest.mark.asyncio
async def test_version_collection_must_match_document(
    uow_factory: async_sessionmaker,
) -> None:
    principal, collection_a = await _principal_and_collection(uow_factory)
    collection_b = Collection(name="other", owner_id=principal.id)
    async with _uow(uow_factory) as uow:
        await uow.collections.add(collection_b)
        await uow.commit()
    document = Document(collection_id=collection_a.id, logical_name="policy.pdf")
    version = DocumentVersion(
        document_id=document.id,
        collection_id=collection_b.id,
        version_number=1,
        content_hash="mismatched-collection",
        original_filename="policy.pdf",
        mime_type="application/pdf",
        size_bytes=1,
        storage_uri="local://policy.pdf",
    )
    async with _uow(uow_factory) as uow:
        await uow.documents.add(document)
        with pytest.raises(DuplicateIdentityError):
            await uow.versions.add(version)
