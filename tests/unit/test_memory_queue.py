from __future__ import annotations

from uuid import uuid4

import pytest

from cited_rag.adapters.queue.memory import MemoryJobQueue
from cited_rag.domain.exceptions import QueueError


@pytest.mark.asyncio
async def test_memory_queue_records_each_wakeup() -> None:
    queue = MemoryJobQueue()
    version_id = uuid4()
    first = await queue.enqueue_ingestion(version_id, "c1", attempt=0)
    second = await queue.enqueue_ingestion(version_id, "c2", attempt=1)
    assert first != second
    assert len(queue.jobs) == 2


@pytest.mark.asyncio
async def test_memory_queue_failure_is_classified() -> None:
    queue = MemoryJobQueue()
    queue.fail_next = True
    with pytest.raises(QueueError):
        await queue.enqueue_ingestion(uuid4(), None)
