from __future__ import annotations

import asyncio
from importlib import metadata
from io import BytesIO
from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError, PdfStreamError

from cited_rag.adapters.parser.preflight import page_count_or_raise
from cited_rag.domain.exceptions import CorruptPdfError, EmptyExtractionError
from cited_rag.domain.parser import ParsedPage, normalize_page_text


class PypdfDocumentParser:
    """Page-aware parser used in tests/dev. Production V1 adapter is Docling."""

    name = "pypdf"

    async def parse(self, source: BinaryIO) -> list[ParsedPage]:
        data = source.read()
        return await asyncio.to_thread(self._parse_bytes, data)

    def _parse_bytes(self, data: bytes) -> list[ParsedPage]:
        page_count_or_raise(data)
        try:
            reader = PdfReader(BytesIO(data), strict=False)
            if reader.is_encrypted:
                reader.decrypt("")
            raw_pages = list(reader.pages)
        except (PdfReadError, PdfStreamError, ValueError, OSError) as exc:
            raise CorruptPdfError() from exc

        version = metadata.version("pypdf")
        parsed: list[ParsedPage] = []
        for index, page in enumerate(raw_pages, start=1):
            try:
                raw = page.extract_text() or ""
            except Exception as exc:
                raise CorruptPdfError(f"failed to extract page {index}") from exc
            normalized = normalize_page_text(raw)
            parsed.append(
                ParsedPage(
                    page_number=index,
                    raw_text=raw,
                    normalized_text=normalized,
                    metadata={
                        "parser": self.name,
                        "parser_version": version,
                        "char_count": len(normalized),
                    },
                )
            )
        if not parsed or all(not page.normalized_text for page in parsed):
            raise EmptyExtractionError()
        return parsed
