# Phase 04 — PDF Parsing and Page Provenance

**Status:** TESTED

## Goal
Parse retained PDFs into ordered page-aware content while preserving exact source-page identity and classifying unsupported/failed extraction cases.

## Prerequisites
Phase 03 COMPLETE.

## Architecture References
ADR-001, HLD Parser Abstraction, PRD FR-04, data-provenance diagram.

## Concepts to Learn
PDF text extraction, layout-aware parsing, page numbering, parser adapters, password-protected files, scanned/image-only limitations.

## Planned Deliverables
`DocumentParser` port, Docling adapter, `PageContent` model, parser error taxonomy, page persistence integration.

## Implementation Tasks
1. Define provider-neutral parser interface.
2. Load source PDF from object storage.
3. Extract ordered page content with original PDF page numbers.
4. Normalize parser output without erasing provenance.
5. Detect corrupt/password-protected/extraction-empty cases.
6. Persist page-level metadata and parser version/config.
7. Keep Docling-specific objects inside the adapter boundary.

## Required Tests
Known multi-page PDF preserves page order, corrupt PDF fails, password-protected PDF fails explicitly, extraction-empty PDF fails/flags unsupported, parser adapter contract test.

## Failure Scenarios
Parser crash mid-document, malformed object, memory/resource limit breach, layout anomalies, zero extractable text.

## Acceptance Criteria
Every extracted text unit can be traced to its original PDF page and unsupported input does not silently produce empty searchable content.

## Definition of Done
Parser adapter, persistence integration, fixtures, tests, review, and Learning notes completed.

## What I Must Be Able to Explain
Why parser choice affects RAG quality? Why page provenance must be captured before chunking? Why OCR-heavy PDFs are out of V1 scope?