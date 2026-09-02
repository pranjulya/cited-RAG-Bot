# ADR-007 — Asynchronous Ingestion

**Status:** Accepted  
**Decision:** PDF ingestion executes asynchronously through a worker/queue boundary instead of keeping the upload HTTP request open until parsing and indexing complete.

## Context

PDF parsing, chunking, embedding generation, dense/sparse indexing, and status transitions can be slow and failure-prone. Query traffic and ingestion traffic should not share the same request lifecycle.

## Decision

The upload API stores the source PDF, creates durable document/job metadata, and enqueues ingestion work. A worker executes the ingestion pipeline and updates status transitions such as:

`UPLOADED -> QUEUED -> PROCESSING -> READY | FAILED`

Use a queue abstraction with Redis-backed infrastructure for V1. The V1 adapter is **arq**. Job identity is `document_version_id`. See ADR-011 for lease, retry, and READY ownership.

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

Phase 03 tests must cover duplicate delivery, crash/restart, bounded retry, and illegal transitions. Partial-index recovery and deletion-while-ingesting are covered in Phases 06–07 and 16 (ADR-011).