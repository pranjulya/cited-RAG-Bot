# Phase 02 — PDF Upload, Object Storage, and Document Lifecycle

**Status:** TESTED

## Goal
Accept PDF uploads into a collection, persist source files through a storage abstraction, create document/version metadata, and expose lifecycle status.

## Prerequisites
Phase 01 COMPLETE.

## Architecture References
PRD FR-01/02/03, ADR-008, HLD Document Service, LLD upload contract.

## Concepts to Learn
Multipart uploads, MIME validation, content hashing, object-storage abstraction, idempotency, document versioning, lifecycle states.

## Planned Deliverables
Collection/document endpoints, upload service, `ObjectStorage` port, local storage adapter, document hash/version policy hooks, status endpoint.

## Implementation Tasks
1. Authenticate with `Authorization: Bearer <api_key>` and authorize collection ownership (`Collection.owner_id`).
2. Validate collection access and PDF envelope.
3. Validate extension/MIME/signature consistently.
4. Stream upload rather than reading unbounded files into memory.
5. Compute content hash while storing.
6. Apply ADR-011 duplicate policy: same hash in the same collection returns the existing document; new bytes create version 1.
7. Create document/version records. The public upload `202` status is `QUEUED` (ADR-011). Until Phase 03 enqueue exists, persist `UPLOADED` internally; do not ship `UPLOADED` as the product `202` contract. Enqueue then `QUEUED` land in Phase 03. Same-hash uploads follow ADR-011 (idempotent return; `FAILED` retries via `FAILED → QUEUED`, not a second document).
8. Store object key by collection/document/version.
9. `GET`/`DELETE /v1/documents/{document_id}` authorize via `document.collection_id` and return 404 for unauthorized.
10. Add status retrieval endpoint.

## Required Tests
Valid PDF upload, non-PDF rejection, empty file rejection, oversized file rejection, duplicate-content policy behavior, storage failure rollback/compensation, collection scoping.

## Failure Scenarios
Storage unavailable, DB write fails after object write, duplicate upload race, malformed MIME, interrupted upload.

## Acceptance Criteria
A valid PDF can be uploaded and persisted without becoming searchable; metadata and object storage remain reconcilable.

## Definition of Done
API, storage adapter, tests, error classification, documentation, and Learning notes completed.

## What I Must Be Able to Explain
Why keep original PDFs? Why hash uploads? Why does `UPLOADED` not mean searchable? How do object-store and DB consistency differ from a single database transaction?