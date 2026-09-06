from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from cited_rag.domain.clock import utc_now
from cited_rag.domain.enums import IngestionJobStatus


@dataclass(frozen=True, slots=True)
class IngestionJob:
    document_version_id: UUID
    id: UUID = field(default_factory=uuid4)
    status: IngestionJobStatus = IngestionJobStatus.PENDING
    attempt_count: int = 0
    last_error: str | None = None
    correlation_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
