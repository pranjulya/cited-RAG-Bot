from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from cited_rag.domain.clock import utc_now
from cited_rag.domain.enums import QueryRunStatus


@dataclass(frozen=True, slots=True)
class QueryRun:
    collection_id: UUID
    principal_id: UUID
    question: str
    id: UUID = field(default_factory=uuid4)
    status: QueryRunStatus = QueryRunStatus.STARTED
    correlation_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
