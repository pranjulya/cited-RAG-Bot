# ADR-003 — Retrieval Store

**Status:** Proposed  
**Decision:** Use Qdrant as the V1 retrieval store for dense and sparse representations, while PostgreSQL remains the durable metadata/provenance system of record.

## Context

The PRD requires dense semantic retrieval, sparse lexical retrieval, hybrid fusion, filtering by collection/document, and replaceable retrieval components.

## Decision

Use a `RetrievalStore` abstraction with Qdrant as the initial implementation.

Each indexed point must carry stable provenance references such as:

- collection_id
- document_id
- document_version
- page_number
- chunk_id

The full authoritative chunk/provenance record remains in PostgreSQL.

## Why This Direction

Qdrant provides a focused retrieval layer and supports dense/sparse retrieval patterns without forcing the application to treat the search index as the source of truth.

## Alternatives Considered

### PostgreSQL + pgvector only

Pros: fewer moving parts.  
Cons: sparse/BM25-quality retrieval and hybrid experimentation become less clean for this learning objective.

### OpenSearch/Elasticsearch

Pros: strong BM25 and hybrid/search capabilities.  
Cons: heavier operational footprint for this project.

### Separate dense and sparse engines

Pros: best-of-breed flexibility.  
Cons: adds consistency and operational complexity too early.

## Consequences

- Two stores must be kept consistent through explicit ingestion/deletion workflows.
- Retrieval data is rebuildable.
- Qdrant-specific APIs stay inside adapters.
- Evaluation must compare dense-only, sparse-only, and hybrid performance.

## Validation Required

Before Accepted, confirm the chosen sparse representation and filtering strategy satisfy the golden retrieval dataset.