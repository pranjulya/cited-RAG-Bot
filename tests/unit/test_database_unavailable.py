from __future__ import annotations

import pytest
from sqlalchemy.exc import DBAPIError, OperationalError

from cited_rag.adapters.persistence.postgres.session import create_engine


@pytest.mark.asyncio
async def test_database_unavailable_fails_clearly() -> None:
    engine = create_engine(
        "postgresql+asyncpg://cited_rag:cited_rag@127.0.0.1:1/cited_rag",
        connect_args={"timeout": 1},
    )
    with pytest.raises((OperationalError, DBAPIError, OSError, ConnectionError)):
        async with engine.connect() as connection:
            await connection.exec_driver_sql("SELECT 1")
    await engine.dispose()
