from __future__ import annotations

import pytest

from cited_rag.domain.exceptions import EmptyUploadError, InvalidPdfError, PayloadTooLargeError
from cited_rag.domain.pdf import PDF_MAGIC, validate_pdf_envelope

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def test_valid_pdf_envelope_accepted() -> None:
    validate_pdf_envelope(
        filename="handbook.pdf",
        content_type="application/pdf",
        size_bytes=len(MINIMAL_PDF),
        head=MINIMAL_PDF[:8],
        max_bytes=1024,
    )


def test_non_pdf_extension_rejected() -> None:
    with pytest.raises(InvalidPdfError):
        validate_pdf_envelope(
            filename="handbook.txt",
            content_type="application/pdf",
            size_bytes=len(MINIMAL_PDF),
            head=MINIMAL_PDF[:8],
            max_bytes=1024,
        )


def test_non_pdf_magic_rejected() -> None:
    with pytest.raises(InvalidPdfError):
        validate_pdf_envelope(
            filename="handbook.pdf",
            content_type="application/pdf",
            size_bytes=4,
            head=b"XXXX",
            max_bytes=1024,
        )


def test_empty_file_rejected() -> None:
    with pytest.raises(EmptyUploadError):
        validate_pdf_envelope(
            filename="handbook.pdf",
            content_type="application/pdf",
            size_bytes=0,
            head=b"",
            max_bytes=1024,
        )


def test_oversized_file_rejected() -> None:
    with pytest.raises(PayloadTooLargeError):
        validate_pdf_envelope(
            filename="handbook.pdf",
            content_type="application/pdf",
            size_bytes=2048,
            head=PDF_MAGIC,
            max_bytes=1024,
        )


def test_mismatched_mime_rejected() -> None:
    with pytest.raises(InvalidPdfError):
        validate_pdf_envelope(
            filename="handbook.pdf",
            content_type="text/plain",
            size_bytes=len(MINIMAL_PDF),
            head=MINIMAL_PDF[:8],
            max_bytes=1024,
        )
