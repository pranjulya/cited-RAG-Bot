from __future__ import annotations

import json
import re

from cited_rag.domain.enums import AnswerStatus
from cited_rag.domain.models.generation import Claim, GenerationPrompt, GroundedGenerationResult

_TOKEN = re.compile(r"[A-Za-z0-9_]+")


def _evidence_items(evidence_json: str) -> list[dict[str, str]]:
    payload = json.loads(evidence_json) if evidence_json else {"evidence": []}
    items = payload.get("evidence", []) if isinstance(payload, dict) else []
    parsed: list[dict[str, str]] = []
    for item in items:
        if isinstance(item, dict) and "id" in item and "text" in item:
            parsed.append({"id": str(item["id"]), "text": str(item["text"])})
    return parsed


class HeuristicGroundedGenerator:
    """Deterministic test/dev generator. Not an LLM."""

    name = "heuristic-v1"

    async def generate(self, prompt: GenerationPrompt) -> GroundedGenerationResult:
        query_tokens = {token.lower() for token in _TOKEN.findall(prompt.question)}
        supporting: list[str] = []
        snippets: list[str] = []
        for item in _evidence_items(prompt.evidence_json):
            text_tokens = {token.lower() for token in _TOKEN.findall(item["text"])}
            if query_tokens & text_tokens:
                supporting.append(item["id"])
                snippets.append(item["text"])
        if not supporting:
            return GroundedGenerationResult(
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                answer=(
                    "The available documents do not provide enough evidence "
                    "to answer this question."
                ),
                claims=(),
                model=self.name,
                input_tokens=len(prompt.question.split()),
                output_tokens=12,
            )
        answer = " ".join(snippets)
        return GroundedGenerationResult(
            status=AnswerStatus.ANSWERED,
            answer=answer,
            claims=(Claim(text=answer, evidence_ids=tuple(supporting)),),
            model=self.name,
            input_tokens=len(prompt.question.split()),
            output_tokens=len(answer.split()),
        )
