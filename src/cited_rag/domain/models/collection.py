from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from cited_rag.domain.clock import utc_now
from cited_rag.domain.enums import CollectionStatus


@dataclass(frozen=True, slots=True)
class Collection:
    name: str
    owner_id: UUID
    id: UUID = field(default_factory=uuid4)
    status: CollectionStatus = CollectionStatus.ACTIVE
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
