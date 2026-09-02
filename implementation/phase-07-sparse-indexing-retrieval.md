# Phase 07 — Sparse Indexing and Retrieval

**Status:** NOT_STARTED

## Goal
Add lexical/sparse retrieval for exact names, identifiers, numbers, rare terms, and phrases while preserving the same chunk identity contract as dense retrieval.

## Prerequisites
Phase 05 COMPLETE.

## References
ADR-003, ADR-004, PRD FR-07, evaluation strategy.

## Concepts to Learn
Sparse vectors, BM25-style ranking, lexical vs semantic retrieval, term frequency, inverse document frequency.

## Planned Deliverables
Sparse encoder/index adapter, sparse retriever port implementation, common `RetrievalCandidate` model.

## Tasks
1. Define sparse indexing representation behind an adapter.
2. Index the same stable chunk IDs used by dense indexing.
3. Enforce collection filters at query time.
4. Return normalized internal candidates with rank and raw score metadata.
5. Add deterministic top-K configuration.
6. Record sparse configuration/version for evaluation reproducibility.

## Tests
Exact identifier match, rare keyword match, number/phrase query, collection isolation, empty result, re-index idempotency.

## Failure Scenarios
Sparse index unavailable, tokenization mismatch, one-sided partial indexing, stale payload.

## Acceptance Criteria
Sparse retrieval can independently recover evidence that dense search may miss and all results obey collection/provenance constraints.

## Definition of Done
Sparse indexing/retrieval tests, docs, review, Learning notes complete.

## What I Must Be Able to Explain
Why vector search alone can fail? Dense vs sparse retrieval? Why exact identifiers often benefit from lexical search?