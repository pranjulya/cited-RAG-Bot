from __future__ import annotations

from dataclasses import dataclass

from cited_rag.domain.enums import NoAnswerReason


@dataclass(frozen=True, slots=True)
class NoAnswerDecision:
    reason: NoAnswerReason
    message: str = "The available documents do not provide enough evidence to answer this question."
