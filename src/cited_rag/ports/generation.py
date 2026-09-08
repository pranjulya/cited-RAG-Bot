from __future__ import annotations

from typing import Protocol

from cited_rag.domain.models.evidence import EvidencePackage
from cited_rag.domain.models.generation import GroundedGenerationResult


class GroundedGenerator(Protocol):
    async def generate(
        self, question: str, evidence: EvidencePackage
    ) -> GroundedGenerationResult: ...
