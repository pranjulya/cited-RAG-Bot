from __future__ import annotations

import logging
from collections.abc import Collection as CollectionType
from uuid import UUID

from cited_rag.domain.enums import AnswerStatus
from cited_rag.domain.exceptions import CitationValidationError
from cited_rag.domain.models.citation import PublicCitation
from cited_rag.domain.models.evidence import EvidencePackage
from cited_rag.domain.models.generation import GroundedGenerationResult
from cited_rag.observability.metrics import metrics

logger = logging.getLogger("cited_rag.citations")


def validate_citations(
    result: GroundedGenerationResult,
    evidence: EvidencePackage,
    *,
    collection_id: UUID,
    allowed_version_ids: CollectionType[UUID] | None = None,
) -> tuple[PublicCitation, ...]:
    """Fail closed on unknown or unapproved evidence IDs. Do not repair."""
    approved = evidence.by_id
    if result.status is AnswerStatus.ANSWERED:
        if not result.claims:
            raise CitationValidationError("answered result has no claims")
        for claim in result.claims:
            if not claim.evidence_ids:
                raise CitationValidationError("answered claim has no evidence ids")
    referenced: list[str] = []
    for claim in result.claims:
        referenced.extend(claim.evidence_ids)
    unique: list[str] = []
    seen: set[str] = set()
    for evidence_id in referenced:
        if evidence_id in seen:
            continue
        seen.add(evidence_id)
        unique.append(evidence_id)
    citations: list[PublicCitation] = []
    for evidence_id in unique:
        record = approved.get(evidence_id)
        if record is None:
            metrics.incr("citation.validation_failed")
            raise CitationValidationError(f"unknown or unapproved evidence id {evidence_id}")
        if record.collection_id != collection_id:
            raise CitationValidationError("evidence does not belong to the requested collection")
        if (
            allowed_version_ids is not None
            and record.document_version_id not in allowed_version_ids
        ):
            raise CitationValidationError("evidence document version is not searchable")
        citations.append(
            PublicCitation(
                document_id=record.document_id,
                document_version_id=record.document_version_id,
                document_name=record.document_name,
                page_start=record.page_start,
                page_end=record.page_end,
            )
        )
    if result.status is AnswerStatus.ANSWERED and not citations:
        raise CitationValidationError("answered result has no approved citations")
    logger.info(
        "citations validated count=%s status=%s",
        len(citations),
        result.status,
        extra={"correlation_id": "-"},
    )
    return tuple(citations)
