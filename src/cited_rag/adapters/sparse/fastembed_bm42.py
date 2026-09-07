from __future__ import annotations

import asyncio

from cited_rag.domain.exceptions import PermanentIngestionError, TransientIngestionError
from cited_rag.domain.indexing import SparseVector
from cited_rag.domain.sparse import SparseEncoderConfig

_DEFAULT_MODEL = "Qdrant/bm42-all-minilm-l6-v2-attentions"


class FastEmbedBm42Encoder:
    """V1 production sparse adapter. Optional extra: cited-rag[sparse]."""

    def __init__(self, config: SparseEncoderConfig | None = None) -> None:
        try:
            from fastembed import SparseTextEmbedding
        except ImportError as exc:
            raise RuntimeError(
                "fastembed is required for CITED_RAG_SPARSE_ENCODER_BACKEND=bm42"
            ) from exc
        self.config = config or SparseEncoderConfig(name="fastembed-bm42", version=_DEFAULT_MODEL)
        self._model = SparseTextEmbedding(model_name=_DEFAULT_MODEL)

    def _encode(self, texts: list[str]) -> list[SparseVector]:
        encoded: list[SparseVector] = []
        for item in self._model.embed(texts):
            encoded.append(
                SparseVector(
                    indices=[int(index) for index in item.indices.tolist()],
                    values=[float(value) for value in item.values.tolist()],
                )
            )
        return encoded

    async def encode_documents(self, texts: list[str]) -> list[SparseVector]:
        if not texts:
            raise PermanentIngestionError(
                "sparse encoding batch is empty",
                failure_code="SPARSE_INDEX_FAILED",
            )
        try:
            return await asyncio.to_thread(self._encode, texts)
        except PermanentIngestionError:
            raise
        except Exception as exc:
            raise TransientIngestionError("sparse encoder failed") from exc

    async def encode_query(self, text: str) -> SparseVector:
        vectors = await self.encode_documents([text])
        return vectors[0]
