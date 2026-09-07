from __future__ import annotations

import logging
from io import BytesIO

from cited_rag.domain.exceptions import (
    PermanentIngestionError,
    StorageError,
    TransientIngestionError,
)
from cited_rag.domain.models.document import DocumentVersion
from cited_rag.domain.models.page import Page
from cited_rag.ports.object_storage import ObjectStorage, key_from_storage_uri, source_pdf_key
from cited_rag.ports.parser import DocumentParser
from cited_rag.ports.repositories import UnitOfWork

logger = logging.getLogger("cited_rag.parsing")


async def persist_parsed_pages(
    uow: UnitOfWork,
    version: DocumentVersion,
    *,
    storage: ObjectStorage,
    parser: DocumentParser,
) -> list[Page]:
    """Load the source PDF, parse pages, persist provenance. Never marks READY."""
    existing = await uow.pages.list_by_version(version.id)
    if existing:
        logger.info(
            "pages already persisted count=%s",
            len(existing),
            extra={"correlation_id": "-"},
        )
        return existing

    try:
        key = key_from_storage_uri(version.storage_uri)
    except ValueError:
        key = source_pdf_key(
            collection_id=version.collection_id,
            document_id=version.document_id,
            version_id=version.id,
        )

    try:
        data = await storage.get(key)
    except StorageError as exc:
        message = str(exc)
        if "missing" in message:
            raise PermanentIngestionError(message, failure_code="PDF_PARSE_FAILED") from exc
        raise TransientIngestionError(message) from exc

    parsed = await parser.parse(BytesIO(data))
    pages = [
        Page(
            document_version_id=version.id,
            page_number=item.page_number,
            raw_text=item.raw_text,
            normalized_text=item.normalized_text,
            extraction_metadata=item.metadata,
        )
        for item in parsed
    ]
    for page in pages:
        await uow.pages.add(page)
    await uow.versions.set_page_count(version.id, len(pages))
    logger.info(
        "parsed pages=%s parser=%s",
        len(pages),
        parser.name,
        extra={"correlation_id": "-"},
    )
    return pages
