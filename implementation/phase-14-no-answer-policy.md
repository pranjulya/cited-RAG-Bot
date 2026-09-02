# Phase 14 — No-Answer Decision Policy

**Status:** NOT_STARTED

## Goal
Implement explicit insufficient-evidence behavior so unsupported questions do not become hallucinated answers.

## Prerequisites
Phases 11–13 COMPLETE. Phase 12 may emit structured abstention; this phase owns policy.

## References
PRD FR-14, HLD No-Answer Flow, evaluation strategy.

## Concepts to Learn
Abstention, evidence sufficiency, false-answer rate, no-answer precision/recall, confidence threshold pitfalls.

## Planned Deliverables
No-answer policy service, decision reasons, configuration hooks, evaluation instrumentation.

## Tasks
1. Define decision points before and after generation.
2. Distinguish no candidates, weak evidence, context rejection, explicit model abstention, and infrastructure failure.
3. Never translate provider/infrastructure errors into `INSUFFICIENT_EVIDENCE`. Zero READY documents → `INSUFFICIENT_EVIDENCE` / `NO_READY_DOCUMENTS`.
4. Keep thresholds configurable and baseline-driven.
5. Emit machine-readable reason codes for evaluation.

## Tests
No retrieval result, weak reranked evidence, explicit model abstention, answerable question, provider timeout not treated as no-answer.

## Failure Scenarios
Over-refusal, false confident answer, arbitrary threshold tuning, provider failure misclassification.

## Acceptance Criteria
Unsupported questions can terminate safely with zero fabricated citations and measurable reason codes.

## Definition of Done
Policy tests, evaluation hooks, review, docs, Learning notes complete.

## What I Must Be Able to Explain
Why abstention is a success case? How no-answer precision/recall differ? Why thresholds must come from evaluation rather than intuition?