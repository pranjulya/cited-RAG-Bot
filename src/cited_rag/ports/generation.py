from __future__ import annotations

from typing import Protocol

from cited_rag.domain.models.generation import GenerationPrompt, GroundedGenerationResult


class GroundedGenerator(Protocol):
    async def generate(self, prompt: GenerationPrompt) -> GroundedGenerationResult: ...
