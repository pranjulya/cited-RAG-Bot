from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from cited_rag.adapters.persistence.postgres.session import create_engine


@pytest.fixture(scope="session")
def qdrant_url() -> str:
    url = os.environ.get("CITED_RAG_QDRANT_URL")
    if not url:
        pytest.skip("CITED_RAG_QDRANT_URL is required for dense index tests")
    return url


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("CITED_RAG_DATABASE_URL")
    if not url:
        pytest.skip("CITED_RAG_DATABASE_URL is required for persistence tests")
    return url


@pytest.fixture(scope="session")
def migrated_database(database_url: str) -> str:
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    os.environ["CITED_RAG_DATABASE_URL"] = database_url
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    return database_url


@pytest_asyncio.fixture
async def engine(migrated_database: str) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(migrated_database)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def uow_factory(engine: AsyncEngine) -> AsyncIterator[async_sessionmaker]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
