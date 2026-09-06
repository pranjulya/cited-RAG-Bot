from __future__ import annotations

from uuid import uuid4

import pytest

from cited_rag.adapters.queue.memory import MemoryJobQueue
from cited_rag.domain.exceptions import QueueError


@pytest.mark.asyncio
async def test_memory_queue_is_idempotent_by_version_id() -> None:
    queue = MemoryJobQueue()
    version_id = uuid4()
    first = await queue.enqueue_ingestion(version_id, "c1")
    second = await queue.enqueue_ingestion(version_id, "c2")
    assert first == second == str(version_id)
    assert len(queue.jobs) == 1


@pytest.mark.asyncio
async def test_memory_queue_failure_is_classified() -> None:
    queue = MemoryJobQueue()
    queue.fail_next = True
    with pytest.raises(QueueError):
        await queue.enqueue_ingestion(uuid4(), None)
