from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from cited_rag.domain.clock import utc_now
from cited_rag.domain.ids import chunk_id_for


@dataclass(frozen=True, slots=True)
class Chunk:
    collection_id: UUID
    document_id: UUID
    document_version_id: UUID
    page_start: int
    page_end: int
    chunk_order: int
    text: str
    content_hash: str
    id: UUID = field(init=False)
    token_count: int | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            chunk_id_for(
                document_version_id=self.document_version_id,
                page_start=self.page_start,
                page_end=self.page_end,
                chunk_order=self.chunk_order,
                content_hash=self.content_hash,
            ),
        )
