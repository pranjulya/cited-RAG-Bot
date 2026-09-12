from __future__ import annotations

from uuid import uuid4

import pytest

from cited_rag.adapters.queue.arq_redis import ArqJobQueue, ingest_job_id
from cited_rag.adapters.queue.memory import MemoryJobQueue
from cited_rag.domain.exceptions import QueueError


class _FakeJob:
    def __init__(self, job_id: str) -> None:
        self.job_id = job_id


class _FakePool:
    def __init__(self) -> None:
        self.job_ids: list[str] = []

    async def enqueue_job(self, _function: str, *_args: object, **kwargs: object) -> _FakeJob:
        job_id = str(kwargs["_job_id"])
        self.job_ids.append(job_id)
        return _FakeJob(job_id)


class _NonePool:
    async def enqueue_job(self, _function: str, *_args: object, **kwargs: object) -> None:
        return None


@pytest.mark.asyncio
async def test_memory_queue_records_each_wakeup() -> None:
    queue = MemoryJobQueue()
    version_id = uuid4()
    first = await queue.enqueue_ingestion(version_id, "c1", attempt=0)
    second = await queue.enqueue_ingestion(version_id, "c2", attempt=1)
    assert first != second
    assert len(queue.jobs) == 2


@pytest.mark.asyncio
async def test_memory_queue_same_attempt_returns_unique_ids() -> None:
    queue = MemoryJobQueue()
    version_id = uuid4()
    first = await queue.enqueue_ingestion(version_id, "c1", attempt=0)
    second = await queue.enqueue_ingestion(version_id, "c1", attempt=0)
    assert first != second
    assert first.startswith(f"ingest:{version_id}:")
    assert second.startswith(f"ingest:{version_id}:")
    assert len(queue.jobs) == 2


@pytest.mark.asyncio
async def test_memory_queue_failure_is_classified() -> None:
    queue = MemoryJobQueue()
    queue.fail_next = True
    with pytest.raises(QueueError):
        await queue.enqueue_ingestion(uuid4(), None)


def test_ingest_job_id_format() -> None:
    version_id = uuid4()
    job_id = ingest_job_id(version_id)
    prefix = f"ingest:{version_id}:"
    assert job_id.startswith(prefix)
    assert len(job_id) == len(prefix) + 8
    assert ingest_job_id(version_id) != job_id


@pytest.mark.asyncio
async def test_arq_enqueue_ingestion_same_attempt_unique_ids() -> None:
    pool = _FakePool()
    queue = ArqJobQueue(pool)  # type: ignore[arg-type]
    version_id = uuid4()
    first = await queue.enqueue_ingestion(version_id, "c1", attempt=0)
    second = await queue.enqueue_ingestion(version_id, "c1", attempt=0)
    assert first != second
    assert pool.job_ids == [first, second]
    assert all(item.startswith(f"ingest:{version_id}:") for item in pool.job_ids)


@pytest.mark.asyncio
async def test_arq_enqueue_ingestion_none_job_returns_id() -> None:
    queue = ArqJobQueue(_NonePool())  # type: ignore[arg-type]
    version_id = uuid4()
    job_id = await queue.enqueue_ingestion(version_id, None, attempt=0)
    assert job_id.startswith(f"ingest:{version_id}:")
