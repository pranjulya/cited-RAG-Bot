from __future__ import annotations

from typing import Protocol
from uuid import UUID


class JobQueue(Protocol):
    async def enqueue_ingestion(
        self,
        document_version_id: UUID,
        correlation_id: str | None = None,
        *,
        attempt: int | None = None,
    ) -> str:
        """Wake a worker for document_version_id. Job id includes attempt."""
