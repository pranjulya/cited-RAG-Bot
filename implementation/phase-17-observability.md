# Phase 17 — Observability

**Status:** NOT_STARTED

## Goal
Standardize ingestion and query telemetry so failures are diagnosable without leaking sensitive raw document/query content. Phases 03–15 already emit stage spans for the capability they add; this phase names, redacts, and completes that instrumentation. It is not the first telemetry.

## Prerequisites
Phases 03 and 15 COMPLETE.

## References
PRD observability requirements, HLD observability architecture, evaluation strategy.

## Concepts to Learn
Structured logs, traces, spans, metrics, high-cardinality labels, correlation IDs, stage latency.

## Planned Deliverables
Logging configuration, tracing instrumentation, metric definitions, provider/stage telemetry, failure-classification dashboards/queries.

## Tasks
1. Propagate request/job correlation IDs.
2. Standardize spans already emitted by Phases 03–15 (parse, chunk, embed, retrieve, fuse, rerank, context, generate, citation validate). Fill any missing stage; do not wait until this phase to start tracing.
3. Record stage latency and candidate counts.
4. Record provider/model/token metadata where safe.
5. Emit counters for ingestion failures, no-answer, citation validation failures, provider failures.
6. Keep high-cardinality IDs in logs/traces rather than metric labels.
7. Redact sensitive raw prompts/evidence by default.

## Tests
Correlation propagation, metric increments, trace span presence, sensitive-data redaction, error classification.

## Failure Scenarios
Telemetry backend unavailable, logging failure, accidental sensitive content logging, cardinality explosion.

## Acceptance Criteria
An engineer can answer “why did this query fail?” from telemetry while raw sensitive content remains protected by default.

## Definition of Done
Telemetry tests, review, runbook notes, Learning notes complete.

## What I Must Be Able to Explain
Logs vs metrics vs traces? Why high-cardinality labels are dangerous? Why RAG requires stage-level tracing?