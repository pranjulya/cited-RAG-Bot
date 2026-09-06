from __future__ import annotations

from typing import Protocol
from uuid import UUID


class JobQueue(Protocol):
    async def enqueue_ingestion(
        self, document_version_id: UUID, correlation_id: str | None = None
    ) -> str:
        """Enqueue by document_version_id. Idempotent for the same version id."""
