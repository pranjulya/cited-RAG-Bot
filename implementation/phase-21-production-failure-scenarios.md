# Phase 21 — Production Failure Scenarios

**Status:** TESTED
**On main:** merged PR #26. **Not REVIEWED:** GitHub PRs #2–#29 have no submitted reviews. **Not COMPLETE:** AGENTS.md DoD was not recorded at close-out.

## Goal
Exercise the failure modes identified in the PRD and master plan so failure behavior is classified, visible, and safe. Production V1 has no silent single-retriever degraded mode.

## Prerequisites
Phases 15–20 COMPLETE.

## References
PRD production failure scenarios, HLD failure principles, `Implementation.md`.

## Concepts to Learn
Chaos/failure testing, fault classification, fail-open vs fail-closed, compensating actions, retry boundaries, resilience testing.

## Planned Deliverables
Scenario matrix, automated/integration failure tests, expected-behavior documentation, recovery runbook notes.

## Tasks
1. Test corrupt/password-protected/extraction-empty PDFs.
2. Test parser, embedding, Qdrant, Redis, reranker, and LLM failures/timeouts.
3. Test partial indexing and worker retry after partial work.
4. Test dense/sparse partial retrieval behavior.
5. Test context overflow and unknown evidence IDs.
6. Test prompt injection and cross-collection leakage attempts.
7. Test deletion races and orphan-artifact reconciliation.
8. Verify every scenario maps to a classified error, retry, no-answer, or safe failure. Do not treat one-retriever answers as an allowed production degraded mode.

## Tests
Each scenario must have an automated test where practical and a documented manual/integration procedure where infrastructure fault injection is required.

## Failure Scenarios
The phase itself covers the complete failure inventory from `Implementation.md` section 12.

## Acceptance Criteria
No known critical failure mode silently returns an apparently successful but ungrounded/cross-tenant answer.

## Definition of Done
Scenario matrix executed, failures classified, recovery notes reviewed, Learning notes complete.

## What I Must Be Able to Explain
Fail-open vs fail-closed? Why provider failure is not the same as insufficient evidence? What is a compensating action? Why test partial writes explicitly?