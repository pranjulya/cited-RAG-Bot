from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from uuid import UUID

from cited_rag.domain.models.evidence import EvidencePackage, EvidenceRecord
from cited_rag.domain.models.retrieval import RerankedEvidence

logger = logging.getLogger("cited_rag.context")


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def build_evidence_package(
    candidates: Sequence[RerankedEvidence],
    *,
    max_items: int,
    token_budget: int,
    document_names: Mapping[UUID, str] | None = None,
) -> EvidencePackage:
    """Assign E1..En from reranked order. Model context is ID + text only."""
    names = document_names or {}
    seen: set[UUID] = set()
    kept: list[EvidenceRecord] = []
    dropped: list[UUID] = []
    used_tokens = 0
    for candidate in candidates:
        if candidate.chunk_id in seen:
            dropped.append(candidate.chunk_id)
            continue
        seen.add(candidate.chunk_id)
        if not candidate.text.strip():
            dropped.append(candidate.chunk_id)
            continue
        if max_items > 0 and len(kept) >= max_items:
            dropped.append(candidate.chunk_id)
            continue
        evidence_id = f"E{len(kept) + 1}"
        formatted = _format_item(evidence_id, candidate.text)
        cost = estimate_tokens(formatted)
        if cost > token_budget - used_tokens:
            dropped.append(candidate.chunk_id)
            continue
        kept.append(
            EvidenceRecord(
                evidence_id=evidence_id,
                chunk_id=candidate.chunk_id,
                collection_id=candidate.collection_id,
                document_id=candidate.document_id,
                document_version_id=candidate.document_version_id,
                document_name=names.get(candidate.document_id, ""),
                page_start=candidate.page_start,
                page_end=candidate.page_end,
                text=candidate.text,
            )
        )
        used_tokens += cost
    context = "\n\n".join(_format_item(record.evidence_id, record.text) for record in kept)
    logger.info(
        "context built count=%s dropped=%s tokens=%s budget=%s",
        len(kept),
        len(dropped),
        used_tokens,
        token_budget,
        extra={"correlation_id": "-"},
    )
    return EvidencePackage(
        records=tuple(kept),
        model_context=context,
        dropped_chunk_ids=tuple(dropped),
    )


def _format_item(evidence_id: str, text: str) -> str:
    return f"[{evidence_id}]\nEvidence:\n{text}"
