# UI-01 — Collections

**Status:** NOT_STARTED

## Goal
Create and list collections in the console. No UUID pasting.

## Prerequisites
UI-00 COMPLETE (merged).

## References
`src/cited_rag/api/routes/collections.py`, ADR-011 collection ownership, ADR-012 §3.

## Concepts to Learn
List vs get-by-id, principal-scoped index, empty states.

## Planned Deliverables
`GET /v1/collections` (principal’s collections: id, name, status). Collection list + create form in the UI.

## Tasks
1. Backend: list collections for the API principal; tests for empty list, create-then-list, other principal cannot see (single-key V1: ownership still encoded on rows).
2. UI: create collection (existing POST), render list, navigate to a collection shell (documents/ask placeholders).
3. 401 → return to key gate. 400 blank name → inline error.
4. Learning note.

## Tests
API list contract. UI: create appears in list (Testing Library with mocked API or MSW).

## Failure Scenarios
List 503 → error state, retry. Duplicate names allowed unless backend forbids (do not invent uniqueness).

## Acceptance Criteria
Reviewer creates “Acme HR policies” and sees it after refresh without copying an id.

## Definition of Done
List API + UI + Demo + tests + Learning.

## Demo
1. Open console with `replace-me`.
2. Create collection `Acme HR policies`.
3. Show it in the list; click it; URL contains the id but the user never typed it.
4. Refresh: list still there (API, not only React state).

## What I Must Be Able to Explain
Why list was omitted in API V1 and why a console cannot ship without it. How ownership is still collection-scoped.
