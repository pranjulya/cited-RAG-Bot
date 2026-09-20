# UI-06 — Fail-Closed Studio

**Status:** TESTED

## Goal
Make failure modes demoable: bad ingest, abstain, delete, operational 503 vs 200 no-answer.

## Prerequisites
UI-05 COMPLETE.

## References
`docs/operations/failure-scenarios.md`, no-answer reasons, deletion route, query 503 mapping.

## Concepts to Learn
Productizing errors. 200 abstain vs 503 outage. Tombstone vs purge.

## Planned Deliverables
Labeled empty/error/abstain/outage states. Delete control with confirm. After delete: document gone, ask returns `NO_READY_DOCUMENTS`. Optional “studio” panel listing the scenarios for a live demo.

## Tasks
1. Delete in UI (existing DELETE); poll until GET 404.
2. Distinct layouts: abstain, no ready docs, 401, 404, 422 citation, 503 codes.
3. Ingest FAILED row links to `failure_code`.
4. Learning note.

## Tests
UI maps each status/HTTP to the correct panel (unit, no live Qdrant). Delete happy path with mocked API.

## Failure Scenarios
Delete while query in flight — query uses version list at start; do not invent extra locking in UI.

## Acceptance Criteria
A reviewer can run four beats in one sitting: scan fail, abstain, 503 mock or live outage if easy, delete.

## Definition of Done
States + delete + Demo + tests + Learning.

## Demo
1. Image-only PDF → FAILED `PDF_UNSUPPORTED`.
2. Unsupported question → 200 INSUFFICIENT, not an error toast.
3. Delete the READY doc → GET 404; ask → `NO_READY_DOCUMENTS`.
4. Say: “We fail closed. We do not invent a policy when the PDF is gone.”

## What I Must Be Able to Explain
Why no-answer is a successful product outcome. Why delete is tombstone-then-purge. Why 503 must not look like abstain.
