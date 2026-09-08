from __future__ import annotations

import logging
from collections.abc import Sequence

from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.enums import DocumentVersionStatus
from cited_rag.domain.exceptions import PermanentIngestionError, TransientIngestionError
from cited_rag.domain.indexing import DENSE_VECTOR_NAME, PAYLOAD_FIELDS, IndexedPoint
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.document import DocumentVersion
from cited_rag.domain.sparse import SparseEncoderConfig
from cited_rag.ports.embedding import EmbeddingProvider
from cited_rag.ports.repositories import UnitOfWork
from cited_rag.ports.retrieval_store import RetrievalStore
from cited_rag.ports.sparse_encoder import SparseEncoder

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


async def persist_sparse_index(
    chunks: Sequence[Chunk],
    *,
    encoder: SparseEncoder,
    store: RetrievalStore,
    config: EmbeddingConfig,
) -> list[IndexedPoint]:
    """Update sparse named vectors on existing chunk UUIDs. Does not write dense."""
    indexed: list[IndexedPoint] = []
    for start in range(0, len(chunks), config.batch_size):
        batch = list(chunks[start : start + config.batch_size])
        try:
            vectors = await encoder.encode_documents([chunk.text for chunk in batch])
        except PermanentIngestionError:
            raise
        except TimeoutError as exc:
            raise TransientIngestionError(str(exc) or "sparse encoding timed out") from exc
        except TransientIngestionError:
            raise
        except Exception as exc:
            raise TransientIngestionError("sparse encoder failed") from exc
        if len(vectors) != len(batch):
            raise PermanentIngestionError(
                "sparse encoding batch size mismatch",
                failure_code="SPARSE_INDEX_FAILED",
            )
        points = [
            IndexedPoint(
                point_id=chunk.id,
                vectors={},
                payload=_payload(chunk, index_version=config.index_version),
                sparse=vector,
            )
            for chunk, vector in zip(batch, vectors, strict=True)
        ]
        try:
            await store.upsert_sparse(points)
        except PermanentIngestionError:
            raise
        except TransientIngestionError:
            raise
        except Exception as exc:
            raise TransientIngestionError("retrieval store unavailable") from exc
        indexed.extend(points)
    logger.info(
        "sparse indexed count=%s encoder=%s",
        len(indexed),
        encoder.config.name,
        extra={"correlation_id": "-"},
    )
    return indexed


def _canonical_payload(payload: dict[str, str | int]) -> dict[str, str | int]:
    canonical: dict[str, str | int] = {}
    for key in PAYLOAD_FIELDS:
        value = payload.get(key)
        if value is None:
            raise PermanentIngestionError(
                "stored point payload does not match chunk metadata",
                failure_code="INDEX_INCOMPLETE",
            )
        if key in {"page_start", "page_end", "chunk_order"}:
            canonical[key] = int(value)
        else:
            canonical[key] = str(value)
    return canonical


async def assert_dense_and_sparse_complete(
    store: RetrievalStore,
    chunks: Sequence[Chunk],
    *,
    index_version: str,
) -> None:
    for chunk in chunks:
        point = await store.get_point(chunk.id)
        expected = _payload(chunk, index_version=index_version)
        if (
            point is None
            or DENSE_VECTOR_NAME not in point.vectors
            or point.sparse is None
            or not point.sparse.indices
        ):
            raise PermanentIngestionError(
                "dense and sparse artifacts are incomplete",
                failure_code="INDEX_INCOMPLETE",
            )
        try:
            if _canonical_payload(point.payload) != expected:
                raise PermanentIngestionError(
                    "stored point payload does not match chunk metadata",
                    failure_code="INDEX_INCOMPLETE",
                )
        except (TypeError, ValueError) as exc:
            raise PermanentIngestionError(
                "stored point payload does not match chunk metadata",
                failure_code="INDEX_INCOMPLETE",
            ) from exc


async def finalize_ready(
    uow: UnitOfWork,
    version: DocumentVersion,
    chunks: Sequence[Chunk],
    *,
    store: RetrievalStore,
    encoder_config: SparseEncoderConfig,
    index_version: str,
) -> DocumentVersion:
    """READY only after PostgreSQL chunks, both named vectors, and payload match."""
    await assert_dense_and_sparse_complete(store, chunks, index_version=index_version)
    await uow.versions.set_sparse_encoder_config(version.id, encoder_config.as_record())
    ready = await uow.versions.transition(
        version.id,
        DocumentVersionStatus.PROCESSING,
        DocumentVersionStatus.READY,
    )
    await uow.documents.set_active_version(version.document_id, version.id)
    logger.info("version READY after dense+sparse", extra={"correlation_id": "-"})
    return ready
