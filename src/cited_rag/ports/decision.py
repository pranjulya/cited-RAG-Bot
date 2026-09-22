from __future__ import annotations

from typing import Protocol

from cited_rag.domain.models.decision import EvidenceDecision
from cited_rag.domain.models.evidence import EvidencePackage


class EvidenceDecisioner(Protocol):
    async def decide(self, question: str, evidence: EvidencePackage) -> EvidenceDecision: ...
