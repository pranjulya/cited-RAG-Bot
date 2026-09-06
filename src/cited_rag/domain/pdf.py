from __future__ import annotations

from cited_rag.domain.exceptions import EmptyUploadError, InvalidPdfError, PayloadTooLargeError

PDF_MAGIC = b"%PDF"
ALLOWED_PDF_CONTENT_TYPES = frozenset({"application/pdf", "application/octet-stream"})


def validate_pdf_envelope(
    *,
    filename: str | None,
    content_type: str | None,
    size_bytes: int,
    head: bytes,
    max_bytes: int,
) -> None:
    if size_bytes <= 0 or not head:
        raise EmptyUploadError()
    if size_bytes > max_bytes:
        raise PayloadTooLargeError()
    name = (filename or "").lower()
    if not name.endswith(".pdf"):
        raise InvalidPdfError("filename must end with .pdf")
    if content_type:
        mime = content_type.split(";", 1)[0].strip().lower()
        if mime not in ALLOWED_PDF_CONTENT_TYPES:
            raise InvalidPdfError("content type must be application/pdf")
    if not head.startswith(PDF_MAGIC):
        raise InvalidPdfError("file signature is not PDF")
