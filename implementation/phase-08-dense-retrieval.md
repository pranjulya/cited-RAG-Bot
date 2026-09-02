# Phase 08 — Dense Retrieval

**Status:** NOT_STARTED

## Goal
Implement collection-scoped semantic retrieval over dense embeddings and expose deterministic candidates for downstream hybrid fusion.

## Prerequisites
Phase 06 COMPLETE.

## References
PRD FR-06, HLD Dense Retriever, evaluation strategy.

## Concepts to Learn
Top-K retrieval, similarity scores, query embeddings, metadata filtering, candidate models, recall-oriented retrieval.

## Planned Deliverables
Dense retriever service, query-embedding integration, `RetrievalCandidate` output, telemetry hooks.

## Tasks
1. Embed incoming query via embedding provider port.
2. Search dense index with mandatory collection filter.
3. Return stable chunk IDs, rank, score, and provenance metadata.
4. Make candidate count configurable.
5. Record retrieval latency and candidate counts.
6. Expose deterministic fake for unit/evaluation tests.

## Tests
Semantic paraphrase retrieval, collection isolation, no-result behavior, top-K truncation, provider failure, retrieval-store failure.

## Failure Scenarios
Embedding timeout, Qdrant unavailable, malformed payload, missing authoritative chunk metadata.

## Acceptance Criteria
Dense retrieval produces auditable candidates without leaking cross-collection chunks.

## Definition of Done
Unit/integration tests, telemetry hooks, review, docs, Learning notes complete.

## What I Must Be Able to Explain
What does Recall@K measure? Why should first-stage retrieval optimize recall before precision? Why must collection filtering happen inside retrieval?