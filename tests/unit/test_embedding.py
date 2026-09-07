from __future__ import annotations

import pytest

from cited_rag.adapters.embedding import create_embedding_provider
from cited_rag.adapters.embedding.hashing import HashEmbeddingProvider
from cited_rag.domain.embedding import EmbeddingConfig
from cited_rag.domain.exceptions import PermanentIngestionError


def test_embedding_config_rejects_invalid_dimension() -> None:
    with pytest.raises(ValueError, match="dimension"):
        EmbeddingConfig(dimension=0)


def test_embedding_config_rejects_invalid_batch_size() -> None:
    with pytest.raises(ValueError, match="batch"):
        EmbeddingConfig(dimension=8, batch_size=0)


@pytest.mark.asyncio
async def test_hash_provider_is_deterministic_and_normalized() -> None:
    provider = HashEmbeddingProvider(dimension=8)
    first = await provider.embed_documents(["alpha", "beta"])
    second = await provider.embed_documents(["alpha", "beta"])
    query = await provider.embed_query("alpha")
    assert first == second
    assert len(first) == 2
    assert all(len(vector) == 8 for vector in first)
    assert first[0] != first[1]
    assert query == first[0]
    assert pytest.approx(sum(value * value for value in first[0]), rel=1e-6) == 1.0


@pytest.mark.asyncio
async def test_hash_provider_rejects_empty_batch() -> None:
    provider = HashEmbeddingProvider(dimension=8)
    with pytest.raises(PermanentIngestionError, match="empty"):
        await provider.embed_documents([])


def test_embedding_factory_rejects_unknown_backend() -> None:
    class _Settings:
        embedding_backend = "openai"
        embedding_dimension = 8

    with pytest.raises(ValueError, match="unsupported embedding backend"):
        create_embedding_provider(_Settings())  # type: ignore[arg-type]
