from __future__ import annotations

from dataclasses import dataclass

from cited_rag.domain.enums import AnswerStatus


@dataclass(frozen=True, slots=True)
class GenerationPrompt:
    """Trusted system text, user question, and untrusted evidence stay separate."""

    system: str
    question: str
    evidence_json: str


@dataclass(frozen=True, slots=True)
class Claim:
    text: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GroundedGenerationResult:
    status: AnswerStatus
    answer: str
    claims: tuple[Claim, ...]
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
