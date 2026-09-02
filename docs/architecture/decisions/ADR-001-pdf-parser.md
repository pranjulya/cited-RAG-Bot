# ADR-001 — PDF Parser

**Status:** Accepted  
**Decision:** Use Docling as the primary V1 PDF parser behind a parser interface.

## Context

The system requires page-aware parsing because citations must map back to exact PDF pages. Parsing quality also affects chunking, tables, layout preservation, retrieval quality, and citation correctness.

## Decision

Use a `DocumentParser` abstraction. The initial implementation uses Docling as the primary parser because V1 benefits from richer layout-aware extraction and page provenance.

The domain layer must not depend directly on Docling types.

Conceptual contract:

```python
class DocumentParser(Protocol):
    async def parse(self, source: BinaryIO) -> list[ParsedPage]:
        ...
```

`ParsedDocument` must expose normalized page-aware content independent of the parser library.

## Alternatives Considered

### PyMuPDF / pypdf

Pros: lightweight, fast, simple.  
Cons: weaker abstraction for complex layout/tables; more custom normalization work.

### Unstructured

Pros: document-oriented parsing pipeline.  
Cons: heavier dependency/operational surface for the focused V1.

## Consequences

- Parser dependency remains replaceable.
- Page provenance is mandatory in the parser output contract.
- Scanned/OCR-heavy PDFs remain outside guaranteed V1 support.
- Parser benchmarks must include normal text PDFs, tables, headers/footers, and multi-column layouts.

## Validation Required

Parser page-number fidelity is proven in Phase 04 with fixture PDFs (including corrupt, password-protected, and extraction-empty cases). Golden parser samples in the evaluation corpus measure page assignment, not only “chunk ids exist.”