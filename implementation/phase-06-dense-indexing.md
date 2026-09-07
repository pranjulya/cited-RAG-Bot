# Phase 06 — Embedding and Dense Indexing

**Status:** IN_PROGRESS

## Goal
Generate dense embeddings for chunks and index them in the retrieval store with collection-scoped provenance filters.

## Prerequisites
Phase 05 COMPLETE.

## References
ADR-003, ADR-009, HLD retrieval store, LLD retrieval payload contract.

## Concepts to Learn
Embeddings, vector dimensions, cosine similarity, batching, vector-store payload filters, idempotent upsert.

## Planned Deliverables
Embedding provider port, provider adapter, Qdrant dense index adapter, batch indexing service.

## Tasks
1. Define embedding request/response contracts. Query embed is used in Phase 08; the port includes `embed_query` now.
2. Make model/dimension configurable via settings.
3. Create **one** Qdrant collection with named vectors `dense` and `sparse` (sparse may be empty until Phase 07).
4. Batch chunks to embedding provider.
5. Upsert `dense` using chunk UUID point ids. Do not use free-form string ids.
6. Store collection/document/version/page payload fields from LLD §17. Authoritative text stays in PostgreSQL.
7. Do **not** mark the document version `READY`.
8. Handle retries/idempotent re-indexing.

## Tests
Embedding adapter contract, batch sizing, deterministic UUID point IDs, payload indexes exist, duplicate upsert, provider timeout, Qdrant failure. A filtered dummy query may exist; dense retrieval product behavior is Phase 08.

## Acceptance Criteria
Every persisted chunk can be densely upserted onto the shared named-vector collection. The collection is not dense-only. Versions are not queryable as READY yet.

## Failure Scenarios
Dimension mismatch, partial batch failure, rate limit, index unavailable, metadata mismatch.

## Definition of Done
Dense index integration/tests/review/Learning notes complete.

## What I Must Be Able to Explain
What is an embedding? Why vector dimensions must match the index? Why metadata filters are a security requirement, not only a performance optimization?