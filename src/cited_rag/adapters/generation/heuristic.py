from __future__ import annotations

import json
import re

from cited_rag.domain.enums import AnswerStatus
from cited_rag.domain.models.generation import Claim, GenerationPrompt, GroundedGenerationResult

_TOKEN = re.compile(r"[A-Za-z0-9_]+")

# Function words carry no evidence. Without this list, "how many days do employees get"
# matches any chunk that says "employees" and the answer quotes unrelated text.
_STOPWORDS = frozenset(
    """
    a an and are as at be been but by can could did do does for from had has have how
    i if in into is it its may me might more most my no not of on or our should so than
    that the their them then there these they this to too was we were what when where
    which who whom why will with would you your
    """.split()
)
# An item must share at least this fraction of the best item's score to be quoted.
_RELEVANCE_RATIO = 0.5


def _content_tokens(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN.findall(text) if token.lower() not in _STOPWORDS}


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
        query_tokens = _content_tokens(prompt.question)
        scored: list[tuple[int, str, str]] = []
        for item in _evidence_items(prompt.evidence_json):
            overlap = len(query_tokens & _content_tokens(item["text"]))
            if overlap:
                scored.append((overlap, item["id"], item["text"]))
        best = max((score for score, _, _ in scored), default=0)
        relevant = [
            (item_id, text)
            for score, item_id, text in sorted(scored, key=lambda row: -row[0])
            if score >= best * _RELEVANCE_RATIO
        ]
        supporting = [item_id for item_id, _ in relevant]
        snippets = [text for _, text in relevant]
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
