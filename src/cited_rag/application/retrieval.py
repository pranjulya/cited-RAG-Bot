from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from uuid import UUID

from cited_rag.domain.enums import RetrievalSource
from cited_rag.domain.exceptions import DenseRetrievalError, TransientIngestionError
from cited_rag.domain.indexing import SearchHit
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.retrieval import RetrievedCandidate
from cited_rag.ports.embedding import EmbeddingProvider
from cited_rag.ports.retrieval_store import RetrievalStore
from cited_rag.ports.sparse_encoder import SparseEncoder

logger = logging.getLogger("cited_rag.retrieval")


async def retrieve_dense(
    query: str,
    *,
    embedder: EmbeddingProvider,
    store: RetrievalStore,
    chunks: Sequence[Chunk],
    collection_id: UUID,
    document_version_ids: Sequence[UUID],
    top_k: int,
) -> list[RetrievedCandidate]:
    """Semantic retrieval. Callers pass READY version ids for production search."""
    started = time.perf_counter()
    if not document_version_ids or top_k < 1:
        logger.info(
            "dense retrieval empty-filter count=0 top_k=%s",
            top_k,
            extra={"correlation_id": "-"},
        )
        return []
    try:
        vector = await embedder.embed_query(query)
        hits = await store.search_dense(
            vector,
            collection_id=collection_id,
            document_version_ids=document_version_ids,
            top_k=top_k,
        )
    except DenseRetrievalError:
        raise
    except TimeoutError as exc:
        raise DenseRetrievalError(str(exc) or "dense embedding timed out") from exc
    except TransientIngestionError as exc:
        raise DenseRetrievalError(str(exc) or "dense retrieval store failed") from exc
    except Exception as exc:
        raise DenseRetrievalError("dense retrieval failed") from exc
    candidates = _candidates_from_hits(hits, chunks, RetrievalSource.DENSE)
    logger.info(
        "dense retrieval count=%s top_k=%s latency_ms=%s",
        len(candidates),
        top_k,
        int((time.perf_counter() - started) * 1000),
        extra={"correlation_id": "-"},
    )
    return candidates


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
    return _candidates_from_hits(hits, chunks, RetrievalSource.SPARSE)


def _candidates_from_hits(
    hits: Sequence[SearchHit],
    chunks: Sequence[Chunk],
    source: RetrievalSource,
) -> list[RetrievedCandidate]:
    by_id = {chunk.id: chunk for chunk in chunks}
    candidates: list[RetrievedCandidate] = []
    for rank, hit in enumerate(hits, start=1):
        chunk = by_id.get(hit.point_id)
        if chunk is None:
            continue
        candidates.append(
            RetrievedCandidate(
                chunk_id=chunk.id,
                source=source,
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
