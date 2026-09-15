# Phase 20 — RAG Quality Experiments

**Status:** REVIEWED
**On main:** merged PR #25. **Not COMPLETE:** AGENTS.md COMPLETE requires a recorded Definition of Done (implementation, tests, review, docs, Learning) at close-out; that was not recorded.

## Goal
Benchmark retrieval/generation configurations and use evidence rather than intuition to choose V1 defaults.

## Prerequisites
Phase 19 COMPLETE.

## References
Evaluation strategy, ADR-004/005/010, `Implementation.md`.

## Concepts to Learn
A/B configuration comparison, retrieval baselines, chunk-size experiments, reranking lift, latency-quality-cost tradeoffs.

## Planned Deliverables
Experiment matrix, reproducible config manifests, benchmark reports, recommended V1 configuration.

## Tasks
1. Establish dense-only baseline.
2. Establish sparse-only baseline.
3. Evaluate hybrid RRF.
4. Evaluate hybrid + reranking.
5. Compare candidate counts, chunk settings, and context limits where justified.
6. Record Recall@K, MRR/nDCG, citation metrics, groundedness, no-answer metrics, latency, and token/cost metadata.
7. Select defaults only when results justify them.
8. Document regressions/tradeoffs rather than hiding them.

## Tests
Experiment runner reproducibility, config isolation, result schema validation, baseline comparison.

## Failure Scenarios
Cherry-picked cases, changing multiple variables without tracking, non-reproducible provider versions, optimizing one metric while harming no-answer/citation behavior.

## Acceptance Criteria
The repository contains evidence explaining why the chosen retrieval/reranking/chunk/context defaults were selected.

## Definition of Done
Benchmark results reviewed, recommended config documented, Learning notes complete.

## What I Must Be Able to Explain
Why a better Recall@K can still produce a worse final RAG answer? How do latency and cost constrain reranking? Why keep a simple baseline?