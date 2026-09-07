# Phase 04 — PDF Parsing and Page Provenance

## Why parser choice affects RAG quality

Citations are page-level. If the parser assigns text to the wrong page, retrieval and generation can be fluent and still point at the wrong evidence. Layout-aware parsers (Docling) recover tables and reading order better than a raw `extract_text()` on complex PDFs. V1 still forbids OCR-heavy scans: empty extraction is `PDF_UNSUPPORTED`, not an empty searchable document.

## Why page provenance is captured before chunking

Chunks are derived. Pages are the source-page identity the product cites. If chunking ran first, a later split/merge could invent `page_start`/`page_end` that never existed in the PDF. Phase 04 writes `pages` rows (original page number, raw text, normalized text, parser name/version) while the version stays `PROCESSING`. Chunking is Phase 05. `READY` is still forbidden.

## Why OCR-heavy PDFs are out of V1 scope

Scanned/image-only files need OCR, extra models, and a different quality bar. V1 detects “pages exist but no extractable text” and fails closed (`PDF_UNSUPPORTED`) instead of indexing blank chunks that would later produce ungrounded answers.

## Parser boundary

`DocumentParser.parse(BinaryIO) -> list[ParsedPage]`. Docling types stay in `adapters/parser/docling.py`. Tests and Compose use `CITED_RAG_PARSER_BACKEND=pypdf` so CI does not download layout models. Production can set `docling` after `pip install 'cited-rag[parser]'`.

## Failure taxonomy

- Password-protected → `PDF_PASSWORD_PROTECTED`
- Corrupt/unreadable → `PDF_PARSE_FAILED`
- No extractable text → `PDF_UNSUPPORTED`

These are permanent ingestion failures. The version does not become `READY`.
