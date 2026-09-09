from __future__ import annotations

from uuid import UUID

from cited_rag.domain.exceptions import QueueError


class MemoryJobQueue:
    """Test fake. Production must use Redis/arq."""

    def __init__(self) -> None:
        self.jobs: list[tuple[UUID, str | None, int]] = []
        self.cleanup_jobs: list[tuple[UUID, str | None]] = []
        self.fail_next = False

    async def enqueue_ingestion(
        self,
        document_version_id: UUID,
        correlation_id: str | None = None,
        *,
        attempt: int | None = None,
    ) -> str:
        if self.fail_next:
            self.fail_next = False
            raise QueueError("redis unavailable")
        token = 0 if attempt is None else attempt
        self.jobs.append((document_version_id, correlation_id, token))
        return f"{document_version_id}:{token}"

    async def enqueue_cleanup(
        self,
        document_id: UUID,
        correlation_id: str | None = None,
    ) -> str:
        if self.fail_next:
            self.fail_next = False
            raise QueueError("redis unavailable")
        self.cleanup_jobs.append((document_id, correlation_id))
        return f"cleanup:{document_id}"
