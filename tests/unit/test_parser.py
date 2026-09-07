from __future__ import annotations

from io import BytesIO

import pytest
from tests.pdf_fixtures import CORRUPT_PDF, TWO_PAGE_PDF, make_blank_pdf, make_password_pdf

from cited_rag.adapters.parser import create_document_parser
from cited_rag.adapters.parser.pypdf import PypdfDocumentParser
from cited_rag.domain.exceptions import (
    CorruptPdfError,
    EmptyExtractionError,
    PasswordProtectedPdfError,
)
from cited_rag.domain.parser import ParsedPage, normalize_page_text
from cited_rag.ports.parser import DocumentParser


def test_normalize_keeps_line_breaks_and_collapses_spaces() -> None:
    assert normalize_page_text("  hello   world  \n\n  next\tline  ") == "hello world\nnext line"


def test_parser_factory_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError, match="unsupported parser backend"):
        create_document_parser("unstructured")


def _assert_contract(parser: DocumentParser) -> None:
    assert parser.name
    assert hasattr(parser, "parse")


@pytest.mark.asyncio
async def test_pypdf_parser_preserves_page_order_and_identity() -> None:
    parser = PypdfDocumentParser()
    _assert_contract(parser)
    pages = await parser.parse(BytesIO(TWO_PAGE_PDF))
    assert [page.page_number for page in pages] == [1, 2]
    assert "alpha-page-one" in pages[0].normalized_text
    assert "beta-page-two" in pages[1].normalized_text
    assert pages[0].metadata["parser"] == "pypdf"
    assert all(isinstance(page, ParsedPage) for page in pages)


@pytest.mark.asyncio
async def test_pypdf_parser_rejects_corrupt_pdf() -> None:
    parser = PypdfDocumentParser()
    with pytest.raises(CorruptPdfError) as exc:
        await parser.parse(BytesIO(CORRUPT_PDF))
    assert exc.value.failure_code == "PDF_PARSE_FAILED"


@pytest.mark.asyncio
async def test_pypdf_parser_rejects_password_protected_pdf() -> None:
    parser = PypdfDocumentParser()
    with pytest.raises(PasswordProtectedPdfError) as exc:
        await parser.parse(BytesIO(make_password_pdf()))
    assert exc.value.failure_code == "PDF_PASSWORD_PROTECTED"


@pytest.mark.asyncio
async def test_pypdf_parser_rejects_extraction_empty_pdf() -> None:
    parser = PypdfDocumentParser()
    with pytest.raises(EmptyExtractionError) as exc:
        await parser.parse(BytesIO(make_blank_pdf()))
    assert exc.value.failure_code == "PDF_UNSUPPORTED"


@pytest.mark.asyncio
@pytest.mark.docling
async def test_docling_parser_contract_when_installed() -> None:
    pytest.importorskip("docling")
    parser = create_document_parser("docling")
    _assert_contract(parser)
    pages = await parser.parse(BytesIO(TWO_PAGE_PDF))
    assert [page.page_number for page in pages] == [1, 2]
    assert "alpha-page-one" in pages[0].normalized_text
    assert "beta-page-two" in pages[1].normalized_text
    assert pages[0].metadata["parser"] == "docling"
