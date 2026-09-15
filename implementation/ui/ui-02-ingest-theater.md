# UI-02 — Ingest Theater

**Status:** NOT_STARTED

## Goal
Upload a PDF into the open collection and show lifecycle until `READY` or `FAILED` (with `failure_code` when failed).

## Prerequisites
UI-01 COMPLETE.

## References
`POST /v1/collections/{id}/documents`, `GET /v1/documents/{id}`, document `failure_code` / `failure_message`.

## Concepts to Learn
Async ingest, polling vs later websockets (V1 poll), public status vs internal UPLOADED.

## Planned Deliverables
`GET /v1/collections/{id}/documents` (id, logical_name, status, version, failure_code). Upload dropzone. Timeline: QUEUED → PROCESSING → READY | FAILED.

## Tasks
1. Backend list-documents for a collection the principal owns; 404 if not owned.
2. UI multipart upload; poll GET document until terminal status (timeout message if stuck).
3. FAILED: show `PDF_UNSUPPORTED` / parse errors; do not dump PDF text.
4. Document table in the collection.
5. Learning note.

## Tests
List empty / one READY / one FAILED. UI poll stops on READY. Cross-collection document id is not listed.

## Failure Scenarios
Scanned PDF → FAILED `PDF_UNSUPPORTED`. Worker down → stays QUEUED, UI says waiting, not READY. File without `.pdf` → 400.

## Acceptance Criteria
Text PDF reaches READY in the UI. Failed ingest is labeled, not a generic toast.

## Definition of Done
List+upload+poll UI, tests, Demo, Learning.

## Demo
1. Open Acme HR.
2. Drop a **text** PDF whose first page contains a policy sentence (e.g. leave days).
3. Narrate the status chips until READY.
4. (Optional) Drop a scan or image-only PDF and show FAILED `PDF_UNSUPPORTED`.

## What I Must Be Able to Explain
Why READY requires dense **and** sparse. Why the UI polls instead of trusting 202. Why scanned PDFs fail without OCR.
