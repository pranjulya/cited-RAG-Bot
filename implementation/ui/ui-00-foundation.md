# UI-00 — Foundation

**Status:** TESTED

## Goal
A Vite + React + TypeScript app in `web/` that boots in Docker Compose, requires an API key, and shows live `/health` and `/ready`. Empty workspace only.

## Prerequisites
Backend Phases 00–23 on `main` (**TESTED**, not COMPLETE). ADR-012 Accepted.

## References
`docs/product/glass-box-console.md`, ADR-012, `docker-compose.yml`, `src/cited_rag/main.py` CORS.

## Concepts to Learn
SPA vs API origin, CORS, sessionStorage for secrets, compose multi-service UI.

## Planned Deliverables
`web/` app, `web` compose service, API key gate, health/ready badges, CI typecheck/lint for `web/` (may land fully in UI-08 if this phase at least runs `npm test` locally).

## Tasks
1. Scaffold `web/` with Vite, React, TypeScript.
2. Env: API base URL (compose: `http://api:8000` is server-side only — the **browser** needs the host-published API `http://localhost:8000`).
3. Gate: prompt for API key; persist in `sessionStorage`; send `Authorization: Bearer`.
4. On load, GET `/health` and `/ready`; show ok vs not-ready.
5. Add `web` to compose (dev server or nginx preview). Do not serve the SPA from Python in this phase unless that is strictly simpler.
6. Learning note `Learning/ui-00-foundation.md`.

## Tests
- Key gate rejects empty key.
- After submit, the key is in `sessionStorage` (not `localStorage`) and subsequent `/health` and `/ready` fetches send `Authorization: Bearer <key>`.
- Mock fetch: health ok / ready 503.
- Compose: `web` starts (smoke can be `curl` the UI origin).

## Failure Scenarios
API down → ready badge failed, not a blank white screen. Wrong key is not tested until a `/v1` call (UI-01).

## Acceptance Criteria
From a cold compose up, a reviewer opens the UI origin, enters `replace-me`, and sees health ok without curling.

## Definition of Done
App runs in compose, tests, Demo script below, Learning note, PR.

## Demo
1. `docker compose up --build -d --wait`
2. Open the UI origin in a browser.
3. Paste `replace-me`.
4. Point at green health and ready badges.
5. Show the empty state: “Create a collection in the next phase.”

## What I Must Be Able to Explain
Why the browser cannot use `http://api:8000`. Why the key is not in git. Why this phase does not yet list collections.
