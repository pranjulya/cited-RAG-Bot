from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from cited_rag.domain.clock import utc_now
from cited_rag.domain.enums import DocumentVersionStatus


@dataclass(frozen=True, slots=True)
class Document:
    collection_id: UUID
    logical_name: str
    id: UUID = field(default_factory=uuid4)
    active_version_id: UUID | None = None
    created_at: datetime = field(default_factory=utc_now)
    deleted_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class DocumentVersion:
    document_id: UUID
    collection_id: UUID
    version_number: int
    content_hash: str
    original_filename: str
    mime_type: str
    size_bytes: int
    storage_uri: str
    id: UUID = field(default_factory=uuid4)
    ingestion_status: DocumentVersionStatus = DocumentVersionStatus.UPLOADED
    failure_code: str | None = None
    failure_message: str | None = None
    page_count: int | None = None
    created_at: datetime = field(default_factory=utc_now)
    ready_at: datetime | None = None
