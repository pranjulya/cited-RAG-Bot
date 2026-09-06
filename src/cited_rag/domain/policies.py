from __future__ import annotations

from cited_rag.domain.enums import DocumentVersionStatus
from cited_rag.domain.exceptions import InvalidLifecycleTransitionError

ALLOWED_TRANSITIONS: dict[DocumentVersionStatus, frozenset[DocumentVersionStatus]] = {
    DocumentVersionStatus.UPLOADED: frozenset({DocumentVersionStatus.QUEUED}),
    DocumentVersionStatus.QUEUED: frozenset({DocumentVersionStatus.PROCESSING}),
    DocumentVersionStatus.PROCESSING: frozenset(
        {DocumentVersionStatus.READY, DocumentVersionStatus.FAILED}
    ),
    DocumentVersionStatus.FAILED: frozenset({DocumentVersionStatus.QUEUED}),
    DocumentVersionStatus.READY: frozenset({DocumentVersionStatus.DELETING}),
    DocumentVersionStatus.DELETING: frozenset({DocumentVersionStatus.DELETED}),
    DocumentVersionStatus.DELETED: frozenset(),
}


def assert_lifecycle_transition(
    current: DocumentVersionStatus, target: DocumentVersionStatus
) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidLifecycleTransitionError(current.value, target.value)


def public_ingestion_status(status: DocumentVersionStatus) -> str:
    """Phase 02 persists UPLOADED until Phase 03 enqueues; the product 202/GET status is QUEUED."""
    if status is DocumentVersionStatus.UPLOADED:
        return DocumentVersionStatus.QUEUED.value
    return status.value
