# Phase 07 — Sparse Indexing and Retrieval

**Status:** IN_PROGRESS

## Goal
Add lexical/sparse retrieval for exact names, identifiers, numbers, rare terms, and phrases while preserving the same chunk identity contract as dense retrieval.

## Prerequisites
Phase 06 COMPLETE (Qdrant collection already has named vectors `dense` and `sparse`).

## References
ADR-003, ADR-004, PRD FR-07, evaluation strategy.

## Concepts to Learn
Sparse vectors, BM25-style ranking, lexical vs semantic retrieval, term frequency, inverse document frequency.

## Planned Deliverables
Sparse encoder/index adapter, sparse retriever port implementation, common `RetrievalCandidate` model.

## Tasks
1. Define `SparseEncoder` (default FastEmbed BM42) and sparse retriever ports.
2. Upsert `sparse` on the **same** chunk UUID points created in Phase 06. Do not create a second point identity or a second Qdrant collection.
3. Share the `RetrievedCandidate` model with Phase 08.
4. Enforce `collection_id` and `document_version_id IN (active READY set)` at query time. Before READY finalize, retrieval tests use explicit version ids and must not treat PROCESSING versions as production-searchable.
5. After both named vectors exist for the version, run ingestion-finalize: verify completeness, then `PROCESSING → READY` and set `active_version_id`. Dense-only must remain non-READY / `FAILED` if sparse fails.
6. Record sparse encoder name/version for evaluation reproducibility.

## Tests
Exact identifier match, rare keyword match, number/phrase query, collection isolation, empty result, re-index idempotency.

## Failure Scenarios
Sparse index unavailable, tokenization mismatch, one-sided partial indexing, stale payload.

## Acceptance Criteria
Sparse retrieval can independently recover evidence that dense search may miss; results obey collection and READY/version filters; READY is set only after dense+sparse completeness.

## Definition of Done
Sparse indexing/retrieval tests, docs, review, Learning notes complete.

## What I Must Be Able to Explain
Why vector search alone can fail? Dense vs sparse retrieval? Why exact identifiers often benefit from lexical search?