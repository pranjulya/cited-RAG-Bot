# Phase 03 — Asynchronous Ingestion Worker

**Status:** REVIEWED

## Goal
Move long-running PDF ingestion outside HTTP request handling and make job execution idempotent, observable, and retry-safe.

## Prerequisites
Phase 02 COMPLETE.

## Architecture References
ADR-007, HLD ingestion sequence, LLD ingestion orchestration.

## Concepts to Learn
Background workers, Redis-backed queues, idempotency, retry policy, poison jobs, state transitions, correlation IDs.

## Planned Deliverables
Queue port, Redis-backed adapter, ingestion worker entry point, job payload contract, lifecycle transition service, retry/failure classification.

## Implementation Tasks
1. Define minimal ingestion job payload using `document_version_id` rather than raw PDF bytes. V1 adapter: arq.
2. Enqueue after upload metadata/source storage succeed; version becomes `QUEUED`.
3. Worker claims a processing lease and transitions `QUEUED → PROCESSING`. Do **not** mark `READY` in this phase. Stub later stages as no-ops/checkpoints.
4. Propagate correlation/job IDs into logs/traces. Do not log raw PDF bytes.
5. Add bounded retry for transient infrastructure errors.
6. Mark permanent failures `FAILED` with classified reason.
7. Ensure repeated delivery does not duplicate downstream work.

## Required Tests
Job enqueue, worker consumption, duplicate delivery, transient retry, permanent failure, illegal status transition, worker crash/restart behavior.

## Failure Scenarios
Redis unavailable, job duplicated, worker crashes mid-job, retry exhaustion, DB transition failure.

## Acceptance Criteria
Upload returns without waiting for parsing and every ingestion job has deterministic lifecycle behavior.

## Definition of Done
Queue and worker contracts, integration tests, failure policy, documentation, and Learning notes completed.

## What I Must Be Able to Explain
Why async ingestion? At-least-once delivery implications? Why idempotency is mandatory? Difference between retryable and permanent failures?