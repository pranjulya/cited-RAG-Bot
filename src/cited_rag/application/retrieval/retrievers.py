from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable, Sequence
from uuid import UUID

from cited_rag.domain.enums import RetrievalSource
from cited_rag.domain.exceptions import (
    DenseRetrievalError,
    SparseRetrievalError,
    TransientIngestionError,
)
from cited_rag.domain.indexing import SearchHit
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.retrieval import RetrievedCandidate
from cited_rag.ports.embedding import EmbeddingProvider
from cited_rag.ports.retrieval_store import RetrievalStore
from cited_rag.ports.sparse_encoder import SparseEncoder

logger = logging.getLogger("cited_rag.retrieval")

ChunkLoader = Callable[[Sequence[UUID]], Awaitable[Sequence[Chunk]]]


def chunk_lookup(chunks: Sequence[Chunk]) -> ChunkLoader:
    by_id = {chunk.id: chunk for chunk in chunks}

    async def _load(ids: Sequence[UUID]) -> list[Chunk]:
        return [by_id[chunk_id] for chunk_id in ids if chunk_id in by_id]

    return _load


async def retrieve_dense(
    query: str,
    *,
    embedder: EmbeddingProvider,
    store: RetrievalStore,
    chunks: Sequence[Chunk] = (),
    collection_id: UUID,
    document_version_ids: Sequence[UUID],
    top_k: int,
    load_chunks: ChunkLoader | None = None,
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
    loader = load_chunks if load_chunks is not None else chunk_lookup(chunks)
    loaded = await loader([hit.point_id for hit in hits])
    candidates = _candidates_from_hits(
        hits,
        loaded,
        RetrievalSource.DENSE,
        collection_id=collection_id,
        document_version_ids=document_version_ids,
        error_cls=DenseRetrievalError,
    )
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
    chunks: Sequence[Chunk] = (),
    collection_id: UUID,
    document_version_ids: Sequence[UUID],
    top_k: int,
    load_chunks: ChunkLoader | None = None,
) -> list[RetrievedCandidate]:
    """Lexical retrieval. Callers pass READY version ids for production search."""
    if not document_version_ids or top_k < 1:
        return []
    try:
        vector = await encoder.encode_query(query)
        hits = await store.search_sparse(
            vector,
            collection_id=collection_id,
            document_version_ids=document_version_ids,
            top_k=top_k,
        )
        loader = load_chunks if load_chunks is not None else chunk_lookup(chunks)
        loaded = await loader([hit.point_id for hit in hits])
        return _candidates_from_hits(
            hits,
            loaded,
            RetrievalSource.SPARSE,
            collection_id=collection_id,
            document_version_ids=document_version_ids,
            error_cls=SparseRetrievalError,
        )
    except SparseRetrievalError:
        raise
    except TimeoutError as exc:
        raise SparseRetrievalError(str(exc) or "sparse encoding timed out") from exc
    except TransientIngestionError as exc:
        raise SparseRetrievalError(str(exc) or "sparse retrieval store failed") from exc
    except Exception as exc:
        raise SparseRetrievalError("sparse retrieval failed") from exc


_HIT_METADATA_FIELDS = (
    "collection_id",
    "document_id",
    "document_version_id",
    "page_start",
    "page_end",
    "chunk_order",
)


def _candidates_from_hits(
    hits: Sequence[SearchHit],
    chunks: Sequence[Chunk],
    source: RetrievalSource,
    *,
    collection_id: UUID,
    document_version_ids: Sequence[UUID],
    error_cls: type[DenseRetrievalError] | type[SparseRetrievalError],
) -> list[RetrievedCandidate]:
    by_id = {chunk.id: chunk for chunk in chunks}
    allowed_versions = set(document_version_ids)
    candidates: list[RetrievedCandidate] = []
    for rank, hit in enumerate(hits, start=1):
        chunk = by_id.get(hit.point_id)
        if chunk is None:
            raise error_cls("retrieved point is missing from authoritative chunks")
        if (
            chunk.collection_id != collection_id
            or chunk.document_version_id not in allowed_versions
        ):
            raise error_cls("retrieved point does not match collection/version filter")
        _assert_hit_matches_chunk(hit, chunk, error_cls=error_cls)
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


def _assert_hit_matches_chunk(
    hit: SearchHit,
    chunk: Chunk,
    *,
    error_cls: type[DenseRetrievalError] | type[SparseRetrievalError],
) -> None:
    expected: dict[str, str | int] = {
        "collection_id": str(chunk.collection_id),
        "document_id": str(chunk.document_id),
        "document_version_id": str(chunk.document_version_id),
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "chunk_order": chunk.chunk_order,
    }
    for key in _HIT_METADATA_FIELDS:
        if key not in hit.payload:
            raise error_cls("retrieved point payload is malformed")
        raw = hit.payload[key]
        try:
            actual: str | int = (
                int(raw) if key in {"page_start", "page_end", "chunk_order"} else str(raw)
            )
        except (TypeError, ValueError) as exc:
            raise error_cls("retrieved point payload is malformed") from exc
        if actual != expected[key]:
            raise error_cls("retrieved point payload does not match authoritative chunk")
