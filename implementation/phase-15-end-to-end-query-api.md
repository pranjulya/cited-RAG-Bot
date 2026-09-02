# Phase 15 — End-to-End Query API

**Status:** NOT_STARTED

## Goal
Wire authorization, retrieval, fusion, reranking, context building, grounded generation, no-answer policy, and citation validation into the public collection query endpoint.

## Prerequisites
Phases 09–14 COMPLETE.

## References
PRD API contract, HLD query sequence, LLD orchestration.

## Concepts to Learn
Service orchestration, API boundary validation, dependency injection, error translation, correlation IDs, latency budgets.

## Planned Deliverables
`POST /v1/collections/{collection_id}/query`, query orchestration service, response DTOs, error mapping, request trace propagation.

## Tasks
1. Validate collection access and READY document availability.
2. Execute retrieval → fusion → reranking → context → generation → validation in order.
3. Apply no-answer policy at documented checkpoints.
4. Return answer/status/citations/request ID and safe metadata.
5. Translate classified domain/provider errors to consistent API responses.
6. Record stage timings without logging sensitive raw content by default.

## Tests
Answerable E2E query, unsupported query, multi-document evidence, cross-collection access rejection, provider error, citation-validation failure, correlation-ID propagation.

## Failure Scenarios
No READY docs, partial retrieval failure, reranker timeout, generation error, stale document during query.

## Acceptance Criteria
The public query endpoint produces either a validated grounded answer, a controlled no-answer result, or a classified error; never an unvalidated partial response.

## Definition of Done
E2E tests, error contracts, review, docs, Learning notes complete.

## What I Must Be Able to Explain
Why orchestration belongs outside the route handler? How do domain errors differ from provider errors? Why should partial results not silently become successful answers?