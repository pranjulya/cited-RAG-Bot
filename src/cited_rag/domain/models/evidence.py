from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    evidence_id: str
    chunk_id: UUID
    collection_id: UUID
    document_id: UUID
    document_version_id: UUID
    document_name: str
    page_start: int
    page_end: int
    text: str


@dataclass(frozen=True, slots=True)
class EvidencePackage:
    records: tuple[EvidenceRecord, ...]
    model_context: str
    dropped_chunk_ids: tuple[UUID, ...]

    @property
    def by_id(self) -> dict[str, EvidenceRecord]:
        return {record.evidence_id: record for record in self.records}
