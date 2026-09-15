# UI-03 — Ask + Citations

**Status:** NOT_STARTED

## Goal
The client “wow” screen: question in, grounded answer + page citations out, or a first-class no-answer.

## Prerequisites
UI-02 COMPLETE. At least one READY document in the demo collection.

## References
`POST /v1/collections/{id}/query`, `QueryResponse`, no-answer reasons.

## Concepts to Learn
ANSWERED vs INSUFFICIENT_EVIDENCE vs HTTP 503. Citation DTO without `chunk_id`.

## Planned Deliverables
Ask panel on the collection. Result: answer text, citation chips (`document_name`, pages), or abstain panel with `reason`. `request_id` visible.

## Tasks
1. Typed client for QueryResponse; no extra backend unless needed for UX.
2. Citation chips are not links yet (UI-05). They must show page range.
3. Copy: abstain is success, not an error banner.
4. 413 query too long; empty question disabled.
5. Playwright smoke: mocked or local heuristic answer.
6. Learning note.

## Tests
UI renders ANSWERED with one citation. UI renders INSUFFICIENT with reason. UI renders 503 as outage. Never show an answer when status is INSUFFICIENT.

## Failure Scenarios
No READY docs → `NO_READY_DOCUMENTS`. Heuristic miss on paraphrase → `MODEL_ABSTENTION` (honest). API 503 → outage.

## Acceptance Criteria
A reviewer asks a lexical question on the uploaded policy and sees a citation with a page number. An unsupported question abstains.

## Definition of Done
Ask UI, tests, Demo, Learning. Heuristic is enough; do not add LLM here.

## Demo
1. READY leave-policy PDF.
2. Ask: “How much leave?” → ANSWERED + page citation. Read the JSON-equivalent fields on screen.
3. Ask: “Who leads OpenAI?” → INSUFFICIENT_EVIDENCE, reason shown.
4. Say: “The model is still a stand-in; the citation contract is real. Hosted generation is UI-07.”

## What I Must Be Able to Explain
Why `chunk_id` never appears. Why abstain is 200. Why this screen is not yet the glass box (no E-IDs/stages).
