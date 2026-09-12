from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PublicCitation:
    document_id: UUID
    document_version_id: UUID
    document_name: str
    page_start: int
    page_end: int
