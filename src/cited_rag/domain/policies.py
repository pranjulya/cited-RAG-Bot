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
    """UPLOADED is internal until enqueue; product APIs expose QUEUED after Phase 03."""
    if status is DocumentVersionStatus.UPLOADED:
        return DocumentVersionStatus.QUEUED.value
    return status.value
