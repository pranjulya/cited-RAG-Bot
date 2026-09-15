# UI-05 — Page Proof

**Status:** NOT_STARTED

## Goal
Click a citation and see that page of the source PDF. Trust becomes visual.

## Prerequisites
UI-04 COMPLETE.

## References
Object storage, `source_pdf_key`, document ownership, ADR-008.

## Concepts to Learn
Authenticated file download vs public bucket URL. Page vs byte offset.

## Planned Deliverables
Authenticated `GET /v1/documents/{id}/content` (PDF bytes) or page-render route, collection/owner checked, deleted documents 404. UI PDF viewer jumps to `page_start` (and highlights through `page_end` if cheap).

## Tasks
1. Backend stream from object storage; never return `storage_uri` to the browser.
2. UI: pdf.js or equivalent; citation click sets page.
3. Tombstoned document: viewer 404.
4. Learning note.

## Tests
Owner can fetch; other collection 404. DELETE then content 404. UI requests include Bearer.

## Failure Scenarios
Missing object → 503 storage. Password PDF already failed ingest; viewer only for READY/failed-with-file policy: only non-deleted documents with stored bytes.

## Acceptance Criteria
Citation click shows the policy sentence on the cited page without downloading via a public URL.

## Definition of Done
Auth PDF route + viewer, tests, Demo, Learning.

## Demo
1. Answered query with page 1 citation.
2. Click the chip; the PDF viewer is on page 1; read the sentence aloud.
3. Say: “The model never sent this page number; the API did after validating E1.”

## What I Must Be Able to Explain
Why a signed public S3 URL is out of V1 (authz is collection-scoped in-app). Why the viewer is not a second source of citation truth.
