# Phase 16 — Document Deletion and Index Consistency

**Status:** NOT_STARTED

## Goal
Delete or tombstone documents safely so no stale searchable chunks remain in derived retrieval indexes.

## Prerequisites
Phases 02, 06, 07, and 15 COMPLETE.

## References
PRD FR-16, HLD data ownership model, LLD cleanup behavior.

## Concepts to Learn
Tombstoning, eventual consistency, compensating cleanup, idempotent deletion, orphan detection.

## Planned Deliverables
Deletion service, cleanup job, search-index purge by document/version, source-storage cleanup policy, reconciliation checks.

## Tasks
1. Authorize delete request.
2. Mark document/version non-queryable before destructive cleanup.
3. Remove dense and sparse retrieval artifacts by authoritative identifiers.
4. Apply source PDF retention/deletion policy.
5. Delete or retain metadata according to audit needs.
6. Make cleanup retry-safe and idempotent.
7. Add reconciliation query/test for orphan search points.

## Tests
Normal deletion, repeated delete, index cleanup failure, storage cleanup failure, deletion during ingestion, deletion during query, orphan prevention.

## Failure Scenarios
Qdrant unavailable, worker crash mid-cleanup, source deletion succeeds but metadata update fails, concurrent query race.

## Acceptance Criteria
A deleted/tombstoned document cannot participate in future retrieval and failed cleanup is visible/retryable.

## Definition of Done
Deletion integration tests, reconciliation checks, review, docs, Learning notes complete.

## What I Must Be Able to Explain
Why tombstone before cleanup? Why distributed deletion is not one atomic transaction? How do idempotency and reconciliation reduce orphan risk?