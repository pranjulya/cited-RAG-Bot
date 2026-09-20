# UI-05 — Page Proof

**Status:** TESTED

## Goal
Click a citation and see that page of the source PDF. One canonical download route; the browser turns pages locally.

## Prerequisites
UI-04 COMPLETE.

## References
`ObjectStorage.get`, `source_pdf_key`, `GET /v1/documents/{id}`, ADR-008, ADR-012.

## Concepts to Learn
Authenticated file download vs public bucket URL. 1-based PDF page numbers already used by the parser and citations.

## Canonical endpoint (locked)

```http
GET /v1/documents/{document_id}/content
Authorization: Bearer <api_key>
```

No query string. No page-render / raster route in V1. No `Range` requirement in V1 (full object).

| Rule | Value |
|---|---|
| Auth | Same Bearer as other `/v1/*`. Missing/wrong key → **401** `unauthorized`. |
| Authorization | Principal must own the document’s collection. Else **404** `document_not_found` (same as GET document; do not leak existence). |
| Deleted | `deleted_at` set → **404** `document_not_found`. |
| Missing document | **404** `document_not_found`. |
| Bytes | Object for the document’s **active** version if `active_version_id` is set; otherwise the latest version that still has a storage URI. |
| `Content-Type` | `application/pdf` |
| `Cache-Control` | `private, no-store` |
| Body | Raw PDF bytes. Never JSON. Never `storage_uri`. |
| Size limit | If `len(bytes) > settings.max_upload_bytes` → **413** `too_large` (same cap as upload). |
| Storage failure | `StorageError` / missing object that metadata still points at → **503** `storage_unavailable`. |
| Page numbers | Citations `page_start` / `page_end` are **1-based** and match `ParsedPage.page_number`. The UI uses pdf.js (or equivalent) to **seek to `page_start`**. The API does not crop pages. |

## Planned Deliverables
The route above. UI viewer: on citation click, `GET .../content` with Bearer, then `viewer.currentPageNumber = page_start`.

## Tasks
1. Stream/load from object storage; never put `storage_uri` in headers or body.
2. UI pdf.js; citation click sets page.
3. Learning note.

## Tests
- Owner + READY doc → 200, `Content-Type: application/pdf`, magic `%PDF`.
- Wrong key → 401.
- Other collection’s id → 404.
- After DELETE → 404.
- Missing blob, row still present → 503 `storage_unavailable`.
- Oversized fixture → 413.
- UI fetch includes `Authorization`.

## Failure Scenarios
Password PDFs never become READY; this route is not an OCR path. Viewer is not a second citation authority.

## Acceptance Criteria
Citation click shows the cited **1-based** page from an authenticated PDF response, not a public URL.

## Definition of Done
This one route + viewer, tests, Demo, Learning.

## Demo
1. Answered query with page 1 citation.
2. Click the chip; viewer is on page 1; read the sentence.
3. Say: “The model never sent this page number; the API did after validating E1.”

## What I Must Be Able to Explain
Why there is no `/pages/{n}` raster. Why 404 is used for both missing and unauthorized. Why page index is 1-based.
