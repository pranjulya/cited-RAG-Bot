from __future__ import annotations

from enum import StrEnum


class CollectionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class DocumentVersionStatus(StrEnum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
    DELETING = "DELETING"
    DELETED = "DELETED"


class IngestionJobStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class QueryRunStatus(StrEnum):
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RetrievalSource(StrEnum):
    DENSE = "DENSE"
    SPARSE = "SPARSE"


class AnswerStatus(StrEnum):
    ANSWERED = "ANSWERED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class NoAnswerReason(StrEnum):
    NO_READY_DOCUMENTS = "NO_READY_DOCUMENTS"
    NO_RETRIEVAL_RESULTS = "NO_RETRIEVAL_RESULTS"
    WEAK_EVIDENCE = "WEAK_EVIDENCE"
    CONTEXT_EMPTY = "CONTEXT_EMPTY"
    MODEL_ABSTENTION = "MODEL_ABSTENTION"
