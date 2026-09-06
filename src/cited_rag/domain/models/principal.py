from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from cited_rag.domain.clock import utc_now


@dataclass(frozen=True, slots=True)
class ApiPrincipal:
    name: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
