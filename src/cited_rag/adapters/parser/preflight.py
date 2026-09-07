from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError, PdfStreamError

from cited_rag.domain.exceptions import CorruptPdfError, PasswordProtectedPdfError


def page_count_or_raise(data: bytes) -> int:
    """Classify corrupt/password PDFs before a parser backend runs."""
    try:
        reader = PdfReader(BytesIO(data), strict=False)
    except (PdfReadError, PdfStreamError, ValueError, OSError) as exc:
        raise CorruptPdfError() from exc

    if reader.is_encrypted:
        try:
            unlocked = int(reader.decrypt("")) > 0
        except (FileNotDecryptedError, PdfReadError, ValueError, TypeError):
            unlocked = False
        if not unlocked:
            raise PasswordProtectedPdfError()

    try:
        count = len(reader.pages)
    except (PdfReadError, PdfStreamError, ValueError) as exc:
        raise CorruptPdfError() from exc
    if count <= 0:
        raise CorruptPdfError()
    return count
