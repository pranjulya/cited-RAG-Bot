# Phase 03 — Asynchronous Ingestion

## Why async ingestion?

Parsing, chunking, and indexing are slow and failure-prone. The upload HTTP request should only persist the PDF and metadata, then return `202 QUEUED`. A worker owns `QUEUED → PROCESSING`. `READY` is still forbidden here; later phases add parse/index completeness.

## At-least-once delivery

The queue may deliver the same `document_version_id` more than once. The worker is idempotent: a live processing lease skips duplicates; a completed stub (`job SUCCEEDED` and version `PROCESSING`) skips again. Crashes drop the lease (`updated_at` older than the lease window) so another delivery can resume.

## Why idempotency is mandatory

Retries reuse the same version identity. Creating a second job, document, or version on redelivery would fork provenance. The idempotency key is `document_version_id` (arq `_job_id` and the unique `ingestion_jobs.document_version_id` row).

## Retryable vs permanent failures

Transient errors (timeouts, brief DB/Redis faults) increment `attempt_count` and re-raise for another delivery, bounded by `ingestion_max_attempts`. Exhaustion and permanent errors (missing version, illegal state, missing source in later phases) mark the version `FAILED` with `failure_code`. `FAILED → QUEUED` is an explicit retry on a later upload of the same hash, not a second document.

## Correlation IDs

The upload request correlation id is stored on the job and passed in the payload. Logs use that field. Raw PDF bytes are never logged.
