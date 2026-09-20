from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from cited_rag.domain.enums import AnswerStatus, NoAnswerReason
from cited_rag.domain.models.citation import PublicCitation
from cited_rag.domain.models.evidence import EvidenceRecord


@dataclass(frozen=True, slots=True)
class QueryOutcome:
    status: AnswerStatus
    answer: str
    citations: tuple[PublicCitation, ...]
    reason: NoAnswerReason | None = None
    evidence: tuple[EvidenceRecord, ...] = ()
    request_id: UUID = field(default_factory=uuid4)
