# Phase 10 — Reranking

**Status:** NOT_STARTED

## Goal
Rerank fused retrieval candidates with a replaceable cross-encoder or hosted reranker and prove whether relevance improves.

## Prerequisites
Phase 09 COMPLETE.

## References
ADR-005, PRD FR-09, HLD Reranker, evaluation strategy.

## Concepts to Learn
Bi-encoder vs cross-encoder, reranking latency, candidate shortlist size, relevance scoring, MRR/nDCG comparison.

## Planned Deliverables
Reranker port, default adapter, timeout policy, reranked candidate model, pre/post-rerank telemetry.

## Tasks
1. Define provider-neutral reranker interface.
2. Accept query plus fused candidate texts/IDs.
3. Return ordered shortlist with rerank score and original retrieval metadata.
4. Configure candidate input and output limits.
5. Production timeout/failure returns `RERANKER_ERROR`. Evaluation may disable rerank via `EvaluationRunConfig`. Do not silently return fused order.
6. Store enough metadata for before/after evaluation.

## Tests
Expected reorder, stable IDs, deterministic fake adapter, timeout behavior, empty list, provider failure, shortlist truncation.

## Failure Scenarios
Reranker timeout, rate limit, malformed response, missing chunk text, no measurable quality gain.

## Acceptance Criteria
Reranker can be swapped without changing query orchestration and evaluation can compare pre/post quality.

## Definition of Done
Adapter contracts, tests, telemetry, review, Learning notes complete.

## What I Must Be Able to Explain
Why rerank after broad retrieval? Cross-encoder vs embedding similarity? Why reranking is not automatically an improvement?