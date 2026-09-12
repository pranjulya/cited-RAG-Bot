from cited_rag.adapters.rerank.overlap import LexicalOverlapReranker
from cited_rag.config import Settings
from cited_rag.ports.reranker import Reranker


def create_reranker(settings: Settings) -> Reranker:
    if settings.reranker_backend == "overlap":
        return LexicalOverlapReranker()
    raise ValueError(f"unsupported reranker backend: {settings.reranker_backend}")
