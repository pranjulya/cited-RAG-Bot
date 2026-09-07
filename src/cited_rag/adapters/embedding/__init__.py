from __future__ import annotations

from cited_rag.adapters.embedding.hashing import HashEmbeddingProvider
from cited_rag.config import Settings
from cited_rag.ports.embedding import EmbeddingProvider


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_backend == "hash":
        return HashEmbeddingProvider(dimension=settings.embedding_dimension)
    raise ValueError(f"unsupported embedding backend: {settings.embedding_backend}")
