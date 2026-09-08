from __future__ import annotations

import re

from cited_rag.application.prompt import build_generation_prompt
from cited_rag.domain.enums import AnswerStatus
from cited_rag.domain.models.evidence import EvidencePackage
from cited_rag.domain.models.generation import Claim, GroundedGenerationResult

_TOKEN = re.compile(r"[A-Za-z0-9_]+")


class HeuristicGroundedGenerator:
    """Deterministic test/dev generator. Not an LLM."""

    name = "heuristic-v1"

    async def generate(self, question: str, evidence: EvidencePackage) -> GroundedGenerationResult:
        _ = build_generation_prompt(question, evidence)
        query_tokens = {token.lower() for token in _TOKEN.findall(question)}
        supporting: list[str] = []
        snippets: list[str] = []
        for record in evidence.records:
            text_tokens = {token.lower() for token in _TOKEN.findall(record.text)}
            if query_tokens & text_tokens:
                supporting.append(record.evidence_id)
                snippets.append(record.text)
        if not supporting:
            return GroundedGenerationResult(
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                answer=(
                    "The available documents do not provide enough evidence "
                    "to answer this question."
                ),
                claims=(),
                model=self.name,
                input_tokens=len(question.split()),
                output_tokens=12,
            )
        answer = " ".join(snippets)
        return GroundedGenerationResult(
            status=AnswerStatus.ANSWERED,
            answer=answer,
            claims=(Claim(text=answer, evidence_ids=tuple(supporting)),),
            model=self.name,
            input_tokens=len(question.split()),
            output_tokens=len(answer.split()),
        )
