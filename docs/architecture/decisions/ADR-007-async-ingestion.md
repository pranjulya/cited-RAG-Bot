# ADR-007 — Asynchronous Ingestion

**Status:** Proposed  
**Decision:** PDF ingestion executes asynchronously through a worker/queue boundary instead of keeping the upload HTTP request open until parsing and indexing complete.

## Context

PDF parsing, chunking, embedding generation, dense/sparse indexing, and status transitions can be slow and failure-prone. Query traffic and ingestion traffic should not share the same request lifecycle.

## Decision

The upload API stores the source PDF, creates durable document/job metadata, and enqueues ingestion work. A worker executes the ingestion pipeline and updates status transitions such as:

`UPLOADED -> PROCESSING -> READY | FAILED`

Use a queue abstraction with Redis-backed infrastructure for V1. Exact worker library is finalized in LLD after comparing operational simplicity and retry semantics.

## Required Properties

- idempotent job handling;
- bounded retries by failure type;
- no searchable document before indexing completes;
- observable job state;
- recovery from worker restart;
- cleanup/compensation for partial index writes.

## Consequences

- API and worker can scale independently.
- Additional infrastructure is required.
- Ingestion must define idempotency and compensation explicitly.
- Status transition ownership must be centralized.

## Validation Required

LLD must define job identifiers, retry policy, partial-failure recovery, and deletion behavior while ingestion is active.