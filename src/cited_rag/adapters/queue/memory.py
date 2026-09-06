from __future__ import annotations

from uuid import UUID

from cited_rag.domain.exceptions import QueueError


class MemoryJobQueue:
    """In-process queue. Does not run workers; tests drain by calling the orchestrator."""

    def __init__(self) -> None:
        self.jobs: list[tuple[UUID, str | None]] = []
        self._ids: set[UUID] = set()
        self.fail_next = False

    async def enqueue_ingestion(
        self, document_version_id: UUID, correlation_id: str | None = None
    ) -> str:
        if self.fail_next:
            self.fail_next = False
            raise QueueError("redis unavailable")
        if document_version_id in self._ids:
            return str(document_version_id)
        self._ids.add(document_version_id)
        self.jobs.append((document_version_id, correlation_id))
        return str(document_version_id)
