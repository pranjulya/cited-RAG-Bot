from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from cited_rag.domain.enums import AnswerStatus, NoAnswerReason
from cited_rag.domain.models.citation import PublicCitation


@dataclass(frozen=True, slots=True)
class QueryOutcome:
    status: AnswerStatus
    answer: str
    citations: tuple[PublicCitation, ...]
    reason: NoAnswerReason | None = None
    request_id: UUID = field(default_factory=uuid4)
