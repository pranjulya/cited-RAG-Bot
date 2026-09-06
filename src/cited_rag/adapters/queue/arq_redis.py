from __future__ import annotations

from uuid import UUID

from arq import ArqRedis
from arq.connections import RedisSettings, create_pool

from cited_rag.domain.exceptions import QueueError

INGEST_FUNCTION_NAME = "ingest_document_version"


class ArqJobQueue:
    def __init__(self, pool: ArqRedis) -> None:
        self._pool = pool

    @classmethod
    async def from_url(cls, redis_url: str) -> ArqJobQueue:
        try:
            pool = await create_pool(RedisSettings.from_dsn(redis_url))
        except Exception as exc:
            raise QueueError("failed to connect to redis") from exc
        return cls(pool)

    async def enqueue_ingestion(
        self, document_version_id: UUID, correlation_id: str | None = None
    ) -> str:
        try:
            job = await self._pool.enqueue_job(
                INGEST_FUNCTION_NAME,
                str(document_version_id),
                correlation_id,
                _job_id=str(document_version_id),
            )
        except Exception as exc:
            raise QueueError("failed to enqueue ingestion job") from exc
        if job is None:
            return str(document_version_id)
        return job.job_id

    async def close(self) -> None:
        await self._pool.close()
