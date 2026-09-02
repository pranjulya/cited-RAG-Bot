# Phase 09 — Hybrid Retrieval and RRF

**Status:** NOT_STARTED

## Goal
Combine dense and sparse candidate sets using Reciprocal Rank Fusion while preserving deterministic chunk identity and auditability.

## Prerequisites
Phases 07 and 08 COMPLETE.

## References
ADR-004, PRD FR-08, HLD Hybrid Coordinator, evaluation strategy.

## Concepts to Learn
Rank fusion, Reciprocal Rank Fusion, score-scale incompatibility, deduplication, deterministic ranking.

## Planned Deliverables
Hybrid retrieval coordinator, RRF implementation, duplicate merger, fused-candidate model, retrieval comparison telemetry.

## Tasks
1. Execute dense and sparse retrieval independently.
2. Deduplicate by stable chunk ID.
3. Apply RRF using rank positions rather than directly mixing incompatible raw scores.
4. Preserve source ranks/scores for diagnostics.
5. Make fusion constant and candidate limits configurable.
6. Empty hit list from one retriever: fuse the other. Operational timeout/unavailable: fail closed (`DENSE_RETRIEVAL_ERROR` / `SPARSE_RETRIEVAL_ERROR`). Do not implement production `ALLOW_SINGLE_RETRIEVER`.
7. Expose fused candidates for evaluation. Dense-only / sparse-only comparisons belong to `EvaluationRunConfig`, not online fallback.

## Tests
Overlapping candidate lists, disjoint lists, one-side **empty hits**, duplicates, deterministic tie handling, dense unavailable, sparse unavailable.

## Failure Scenarios
Dense unavailable, sparse unavailable, both unavailable, duplicate metadata conflict, invalid candidate rank.

## Acceptance Criteria
Hybrid retrieval produces deterministic fused results. Empty lists fuse. Dependency failure fails closed. Evaluation can still run ablations via run config.

## Definition of Done
RRF unit tests, integration tests, fail-closed tests, review, docs, Learning notes complete.

## What I Must Be Able to Explain
Why not simply average dense and sparse scores? What is RRF? What problem does hybrid retrieval solve? Why must hybrid quality be measured against baselines?