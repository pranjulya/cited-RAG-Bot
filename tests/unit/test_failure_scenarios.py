from __future__ import annotations

from cited_rag.domain.enums import NoAnswerReason
from cited_rag.domain.exceptions import (
    CitationValidationError,
    DenseRetrievalError,
    GenerationError,
    RerankerError,
    SparseRetrievalError,
)


def test_provider_failures_are_not_insufficient_evidence() -> None:
    codes = [
        DenseRetrievalError().failure_code,
        SparseRetrievalError().failure_code,
        RerankerError().failure_code,
        GenerationError().failure_code,
        CitationValidationError().failure_code,
    ]
    assert "INSUFFICIENT_EVIDENCE" not in codes
    assert DenseRetrievalError().failure_code == "DENSE_RETRIEVAL_ERROR"
    assert CitationValidationError().failure_code == "CITATION_VALIDATION_FAILED"


def test_no_answer_reasons_are_success_shaped() -> None:
    assert NoAnswerReason.NO_READY_DOCUMENTS.value == "NO_READY_DOCUMENTS"
    assert NoAnswerReason.MODEL_ABSTENTION.value == "MODEL_ABSTENTION"
