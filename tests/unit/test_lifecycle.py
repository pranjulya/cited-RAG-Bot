from __future__ import annotations

import pytest

from cited_rag.domain.enums import DocumentVersionStatus
from cited_rag.domain.exceptions import InvalidLifecycleTransitionError
from cited_rag.domain.policies import assert_lifecycle_transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (DocumentVersionStatus.UPLOADED, DocumentVersionStatus.QUEUED),
        (DocumentVersionStatus.QUEUED, DocumentVersionStatus.PROCESSING),
        (DocumentVersionStatus.PROCESSING, DocumentVersionStatus.READY),
        (DocumentVersionStatus.PROCESSING, DocumentVersionStatus.FAILED),
        (DocumentVersionStatus.FAILED, DocumentVersionStatus.QUEUED),
        (DocumentVersionStatus.READY, DocumentVersionStatus.DELETING),
        (DocumentVersionStatus.DELETING, DocumentVersionStatus.DELETED),
    ],
)
def test_allowed_lifecycle_transitions(
    current: DocumentVersionStatus, target: DocumentVersionStatus
) -> None:
    assert_lifecycle_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (DocumentVersionStatus.UPLOADED, DocumentVersionStatus.PROCESSING),
        (DocumentVersionStatus.UPLOADED, DocumentVersionStatus.READY),
        (DocumentVersionStatus.QUEUED, DocumentVersionStatus.READY),
        (DocumentVersionStatus.QUEUED, DocumentVersionStatus.FAILED),
        (DocumentVersionStatus.PROCESSING, DocumentVersionStatus.QUEUED),
        (DocumentVersionStatus.READY, DocumentVersionStatus.FAILED),
        (DocumentVersionStatus.READY, DocumentVersionStatus.QUEUED),
        (DocumentVersionStatus.FAILED, DocumentVersionStatus.DELETING),
        (DocumentVersionStatus.FAILED, DocumentVersionStatus.READY),
        (DocumentVersionStatus.DELETED, DocumentVersionStatus.QUEUED),
        (DocumentVersionStatus.DELETED, DocumentVersionStatus.UPLOADED),
        (DocumentVersionStatus.DELETING, DocumentVersionStatus.READY),
        (DocumentVersionStatus.READY, DocumentVersionStatus.READY),
    ],
)
def test_invalid_lifecycle_transitions_are_rejected(
    current: DocumentVersionStatus, target: DocumentVersionStatus
) -> None:
    with pytest.raises(InvalidLifecycleTransitionError):
        assert_lifecycle_transition(current, target)
