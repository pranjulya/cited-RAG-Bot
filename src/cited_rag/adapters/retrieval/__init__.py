from __future__ import annotations

from cited_rag.adapters.retrieval.qdrant import QdrantRetrievalStore
from cited_rag.config import Settings
from cited_rag.ports.retrieval_store import RetrievalStore


def create_retrieval_store(settings: Settings) -> RetrievalStore:
    if not settings.qdrant_url:
        raise RuntimeError("CITED_RAG_QDRANT_URL is required to create a retrieval store")
    return QdrantRetrievalStore(
        url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
    )
