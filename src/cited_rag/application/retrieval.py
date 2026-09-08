from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from cited_rag.domain.enums import RetrievalSource
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.retrieval import RetrievedCandidate
from cited_rag.ports.retrieval_store import RetrievalStore
from cited_rag.ports.sparse_encoder import SparseEncoder


async def retrieve_sparse(
    query: str,
    *,
    encoder: SparseEncoder,
    store: RetrievalStore,
    chunks: Sequence[Chunk],
    collection_id: UUID,
    document_version_ids: Sequence[UUID],
    top_k: int,
) -> list[RetrievedCandidate]:
    """Lexical retrieval. Callers pass READY version ids for production search."""
    if not document_version_ids or top_k < 1:
        return []
    vector = await encoder.encode_query(query)
    hits = await store.search_sparse(
        vector,
        collection_id=collection_id,
        document_version_ids=document_version_ids,
        top_k=top_k,
    )
    by_id = {chunk.id: chunk for chunk in chunks}
    candidates: list[RetrievedCandidate] = []
    for rank, hit in enumerate(hits, start=1):
        chunk = by_id.get(hit.point_id)
        if chunk is None:
            continue
        candidates.append(
            RetrievedCandidate(
                chunk_id=chunk.id,
                source=RetrievalSource.SPARSE,
                source_rank=rank,
                source_score=hit.score,
                collection_id=chunk.collection_id,
                document_id=chunk.document_id,
                document_version_id=chunk.document_version_id,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                text=chunk.text,
            )
        )
    return candidates
