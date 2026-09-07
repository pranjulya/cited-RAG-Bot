from __future__ import annotations

import logging
from collections.abc import Sequence

from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.exceptions import PermanentIngestionError, TransientIngestionError
from cited_rag.domain.indexing import DENSE_VECTOR_NAME, IndexedPoint
from cited_rag.domain.models.chunk import Chunk
from cited_rag.ports.embedding import EmbeddingProvider
from cited_rag.ports.retrieval_store import RetrievalStore

logger = logging.getLogger("cited_rag.indexing")


def _payload(chunk: Chunk, *, index_version: str) -> dict[str, str | int]:
    return {
        "collection_id": str(chunk.collection_id),
        "document_id": str(chunk.document_id),
        "document_version_id": str(chunk.document_version_id),
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "chunk_order": chunk.chunk_order,
        "index_version": index_version,
    }


async def persist_dense_index(
    chunks: Sequence[Chunk],
    *,
    embedder: EmbeddingProvider,
    store: RetrievalStore,
    config: EmbeddingConfig,
) -> list[IndexedPoint]:
    """Upsert dense named vectors on chunk UUIDs. Never marks READY. Never writes sparse."""
    await store.ensure_collection(dense_dimension=config.dimension)
    indexed: list[IndexedPoint] = []
    for start in range(0, len(chunks), config.batch_size):
        batch = list(chunks[start : start + config.batch_size])
        try:
            vectors = await embedder.embed_documents([chunk.text for chunk in batch])
        except PermanentIngestionError:
            raise
        except TimeoutError as exc:
            raise TransientIngestionError(str(exc) or "embedding timed out") from exc
        except TransientIngestionError:
            raise
        except Exception as exc:
            raise TransientIngestionError("embedding provider failed") from exc
        if len(vectors) != len(batch):
            raise PermanentIngestionError(
                "embedding batch size mismatch",
                failure_code="EMBEDDING_FAILED",
            )
        points: list[IndexedPoint] = []
        for chunk, vector in zip(batch, vectors, strict=True):
            if len(vector) != config.dimension:
                raise PermanentIngestionError(
                    "embedding dimension mismatch",
                    failure_code="EMBEDDING_FAILED",
                )
            points.append(
                IndexedPoint(
                    point_id=chunk.id,
                    vectors={DENSE_VECTOR_NAME: list(vector)},
                    payload=_payload(chunk, index_version=config.index_version),
                )
            )
        try:
            await store.upsert_dense(points)
        except PermanentIngestionError:
            raise
        except TransientIngestionError:
            raise
        except Exception as exc:
            raise TransientIngestionError("retrieval store unavailable") from exc
        indexed.extend(points)
    logger.info(
        "dense indexed count=%s dimension=%s batch=%s",
        len(indexed),
        config.dimension,
        config.batch_size,
        extra={"correlation_id": "-"},
    )
    return indexed
