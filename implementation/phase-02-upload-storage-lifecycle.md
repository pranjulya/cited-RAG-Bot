# Phase 02 — PDF Upload, Object Storage, and Document Lifecycle

**Status:** NOT_STARTED

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
1. Validate collection access and PDF envelope.
2. Validate extension/MIME/signature consistently.
3. Stream upload rather than reading unbounded files into memory.
4. Compute content hash while storing.
5. Create document/version records in `UPLOADED` state.
6. Store object key by collection/document/version.
7. Return `202 Accepted` with document identifier and status.
8. Add status retrieval endpoint.

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