from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from cited_rag.domain.exceptions import DuplicateContentHashError, DuplicateIdentityError

_HASH_CONSTRAINT = "uq_document_versions_collection_content_hash_active"


def raise_domain_integrity_error(exc: IntegrityError) -> None:
    message = str(exc.orig) if exc.orig is not None else str(exc)
    if _HASH_CONSTRAINT in message:
        raise DuplicateContentHashError() from exc
    raise DuplicateIdentityError() from exc
