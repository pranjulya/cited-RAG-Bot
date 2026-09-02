# ADR-003 — Retrieval Store

**Status:** Accepted  
**Decision:** Use Qdrant as the V1 retrieval store for dense and sparse representations, while PostgreSQL remains the durable metadata/provenance system of record.

## Context

The PRD requires dense semantic retrieval, sparse lexical retrieval, hybrid fusion, filtering by collection/document, and replaceable retrieval components.

## Decision

Use a `RetrievalStore` abstraction with Qdrant as the initial implementation.

Each indexed point uses the chunk UUID as `point_id` and named vectors `dense` and `sparse` on the same point.

Payload must carry:

- collection_id
- document_id
- document_version_id
- page_start
- page_end
- chunk_order
- index_version

Queries must filter `collection_id` and `document_version_id IN (active READY versions)` inside Qdrant. The full authoritative chunk/provenance record remains in PostgreSQL. Schema details are locked in ADR-011.

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

Phase 07 locks the V1 `SparseEncoder` adapter (default FastEmbed BM42) behind the port. Golden retrieval evaluation compares dense-only, sparse-only, and hybrid after the schema exists. Schema and filter rules are not left to coding-time invention (ADR-011).