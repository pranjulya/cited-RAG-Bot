from __future__ import annotations

import asyncio
import logging
import time

from cited_rag.application.prompt import build_generation_prompt
from cited_rag.domain.enums import AnswerStatus
from cited_rag.domain.exceptions import GenerationError
from cited_rag.domain.models.evidence import EvidencePackage
from cited_rag.domain.models.generation import GroundedGenerationResult
from cited_rag.observability.correlation import get_correlation_id
from cited_rag.ports.generation import GroundedGenerator

logger = logging.getLogger("cited_rag.generation")


async def generate_grounded_answer(
    question: str,
    evidence: EvidencePackage,
    *,
    generator: GroundedGenerator,
    timeout_seconds: float,
) -> GroundedGenerationResult:
    started = time.perf_counter()
    try:
        prompt = build_generation_prompt(question, evidence)
        result = await asyncio.wait_for(
            generator.generate(prompt),
            timeout=timeout_seconds,
        )
    except GenerationError:
        raise
    except TimeoutError as exc:
        raise GenerationError(str(exc) or "generation timed out") from exc
    except Exception as exc:
        raise GenerationError("generation failed") from exc
    if result.status not in {AnswerStatus.ANSWERED, AnswerStatus.INSUFFICIENT_EVIDENCE}:
        raise GenerationError("malformed generation result")
    logger.info(
        "generation status=%s claims=%s latency_ms=%s model=%s",
        result.status,
        len(result.claims),
        int((time.perf_counter() - started) * 1000),
        result.model,
        extra={"correlation_id": get_correlation_id()},
    )
    return result
