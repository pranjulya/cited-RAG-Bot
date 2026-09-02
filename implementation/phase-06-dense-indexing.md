# Phase 06 — Embedding and Dense Indexing

**Status:** NOT_STARTED

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
1. Define embedding request/response contracts.
2. Make model/dimension configurable.
3. Batch chunks to embedding provider.
4. Upsert vectors using stable chunk IDs.
5. Store collection/document/version/page metadata as retrieval payload.
6. Enforce collection filtering capability.
7. Handle retries/idempotent re-indexing.

## Tests
Embedding adapter contract, batch sizing, deterministic point IDs, collection filters, duplicate upsert, provider timeout, Qdrant failure.

## Failure Scenarios
Dimension mismatch, partial batch failure, rate limit, index unavailable, metadata mismatch.

## Acceptance Criteria
Every persisted chunk can be densely indexed and queried only within its permitted collection.

## Definition of Done
Dense index integration/tests/review/Learning notes complete.

## What I Must Be Able to Explain
What is an embedding? Why vector dimensions must match the index? Why metadata filters are a security requirement, not only a performance optimization?