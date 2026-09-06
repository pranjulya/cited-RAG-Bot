from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class Page:
    document_version_id: UUID
    page_number: int
    id: UUID = field(default_factory=uuid4)
    raw_text: str | None = None
    normalized_text: str | None = None
    extraction_metadata: dict[str, Any] | None = None
