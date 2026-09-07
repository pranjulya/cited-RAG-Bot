from __future__ import annotations

import asyncio
from collections import defaultdict
from importlib import metadata
from io import BytesIO
from typing import BinaryIO

from cited_rag.adapters.parser.preflight import page_count_or_raise
from cited_rag.domain.exceptions import CorruptPdfError, EmptyExtractionError, PdfParseError
from cited_rag.domain.parser import ParsedPage, normalize_page_text


class DoclingDocumentParser:
    """Docling-backed parser. Domain/application code must not import Docling types."""

    name = "docling"

    def __init__(self) -> None:
        try:
            from docling.document_converter import DocumentConverter  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "docling is not installed; pip install 'cited-rag[parser]' "
                "or set CITED_RAG_PARSER_BACKEND=pypdf"
            ) from exc

    async def parse(self, source: BinaryIO) -> list[ParsedPage]:
        data = source.read()
        return await asyncio.to_thread(self._parse_bytes, data)

    def _parse_bytes(self, data: bytes) -> list[ParsedPage]:
        expected_pages = page_count_or_raise(data)
        try:
            from docling.datamodel.base_models import DocumentStream, InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import DocumentConverter, PdfFormatOption
        except ImportError as exc:
            raise RuntimeError("docling is not installed") from exc

        options = PdfPipelineOptions()
        options.do_ocr = False
        options.do_table_structure = False
        converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)},
        )
        stream = DocumentStream(name="source.pdf", stream=BytesIO(data))
        try:
            result = converter.convert(stream)
        except Exception as exc:
            raise CorruptPdfError("Docling failed to convert PDF") from exc

        texts_by_page: dict[int, list[str]] = defaultdict(list)
        document = result.document
        for item, _level in document.iterate_items():
            text = getattr(item, "text", None)
            if not text:
                continue
            prov = getattr(item, "prov", None) or []
            page_no = prov[0].page_no if prov else None
            if page_no is None:
                continue
            texts_by_page[int(page_no)].append(str(text))

        page_numbers = sorted(texts_by_page) or list(range(1, expected_pages + 1))
        if expected_pages:
            page_numbers = list(range(1, expected_pages + 1))

        try:
            version = metadata.version("docling")
        except metadata.PackageNotFoundError:
            version = "unknown"

        parsed: list[ParsedPage] = []
        for page_number in page_numbers:
            raw = "\n".join(texts_by_page.get(page_number, []))
            normalized = normalize_page_text(raw)
            parsed.append(
                ParsedPage(
                    page_number=page_number,
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
        if len(parsed) != expected_pages:
            raise PdfParseError(
                "parser page count does not match PDF page count",
                failure_code="PDF_PARSE_FAILED",
            )
        return parsed
