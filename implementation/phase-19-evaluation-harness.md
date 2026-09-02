# Phase 19 — Evaluation Harness

**Status:** NOT_STARTED

## Goal
Implement the versioned golden dataset and reusable evaluation runners defined in Step 5.

## Prerequisites
Phases 09–15 COMPLETE.

## References
`docs/evaluation/evaluation-strategy.md`, ADR-010, PRD evaluation requirements.

## Concepts to Learn
Golden datasets, offline evaluation, Recall@K, MRR, nDCG, groundedness, citation correctness/completeness, no-answer metrics, regression testing.

## Planned Deliverables
Golden dataset schema, dataset loader, retrieval runner, reranking runner, answer/citation evaluator, no-answer evaluator, run manifest and result artifacts.

## Tasks
1. Define versioned case format with question, answerability, expected evidence/document/page metadata, tags, and reference answer where appropriate.
2. Implement deterministic retrieval metric calculation.
3. Compare pre/post-rerank results.
4. Evaluate citation validity deterministically and semantic citation correctness separately.
5. Add answer-grounding/unsupported-claim evaluation with explicit judge configuration when LLM judging is used.
6. Add no-answer precision/recall and false-answer-rate calculation.
7. Persist config/model/chunking/retrieval versions with every run.

## Tests
Metric unit tests with hand-calculated examples, dataset validation, missing expected evidence, answerable/unanswerable cases, reproducible run metadata.

## Failure Scenarios
Invalid dataset, judge failure, nondeterministic provider output, missing configuration metadata, metric implementation bug.

## Acceptance Criteria
A single command can evaluate a named configuration and produce reproducible layer-by-layer results.

## Definition of Done
Harness, metric tests, sample golden cases, run docs, review, Learning notes complete.

## What I Must Be Able to Explain
Why evaluate retrieval separately from generation? Recall@K vs MRR vs nDCG? Why LLM-as-judge needs calibration and versioning?