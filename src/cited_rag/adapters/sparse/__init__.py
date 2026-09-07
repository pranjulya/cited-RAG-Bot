from __future__ import annotations

from cited_rag.adapters.sparse.lexical import LexicalSparseEncoder
from cited_rag.config import Settings
from cited_rag.domain.sparse import SparseEncoderConfig
from cited_rag.ports.sparse_encoder import SparseEncoder


def create_sparse_encoder(settings: Settings) -> SparseEncoder:
    config = SparseEncoderConfig(
        name=settings.sparse_encoder_name,
        version=settings.sparse_encoder_version,
    )
    if settings.sparse_encoder_backend == "lexical":
        return LexicalSparseEncoder(config)
    if settings.sparse_encoder_backend == "bm42":
        from cited_rag.adapters.sparse.fastembed_bm42 import FastEmbedBm42Encoder

        return FastEmbedBm42Encoder(config)
    raise ValueError(f"unsupported sparse encoder backend: {settings.sparse_encoder_backend}")
