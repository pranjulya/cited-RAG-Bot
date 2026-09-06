from __future__ import annotations

from uuid import uuid4

import pytest

from cited_rag.domain.enums import RetrievalSource
from cited_rag.domain.models.retrieval import RetrievedCandidate


def test_retrieved_candidate_is_an_immutable_value_object() -> None:
    candidate = RetrievedCandidate(
        chunk_id=uuid4(),
        source=RetrievalSource.DENSE,
        source_rank=1,
        source_score=0.42,
        collection_id=uuid4(),
        document_id=uuid4(),
        document_version_id=uuid4(),
        page_start=3,
        page_end=3,
        text="cited text",
    )
    assert candidate.source is RetrievalSource.DENSE
    with pytest.raises(AttributeError):
        candidate.source_rank = 2  # type: ignore[misc]
