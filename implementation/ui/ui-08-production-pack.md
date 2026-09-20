# UI-08 — Production Pack

**Status:** IN_PROGRESS

## Goal
Ship the console as a production-shaped demo: CI, compose, empty/error/mobile, screenshots, deploy notes, resume copy. No new RAG features.

## Prerequisites
UI-07 COMPLETE.

## References
`.github/workflows/ci.yml`, `docs/operations/deployment.md`, `README.md`, ADR-012.

## Concepts to Learn
Frontend CI, container static hosting, screenshot hygiene (no secrets, no real employee PDFs).

## Planned Deliverables
- `web` production image (nginx or similar) in compose; healthcheck
- CI: lint, typecheck, unit, Playwright smoke against compose
- compose-smoke curls UI origin as well as API
- README: 10-minute client script + screenshots
- `docs/operations/deployment.md`: UI origin, CORS, hosted generator env
- Resume paragraph in `Learning/ui-08-production-pack.md` and interview Q&A additions
- Mark UI phases COMPLETE only if their DoD is met; do not rubber-stamp

## Tasks
1. Production build of `web/` in Docker.
2. CI jobs.
3. Visual pass: desktop + narrow viewport for Ask + glass box.
4. Screenshots without `replace-me` in the frame if possible (show “API key connected”).
5. Update MEMORY Current state after the PR is opened.

## Tests
CI green including UI. Playwright: key → create collection → (optional mocked ingest/query). Compose wait includes `web` healthy.

## Failure Scenarios
CORS misconfig in production origin. API key in a screenshot. Hosted key in the image layers — forbid.

## Acceptance Criteria
A stranger can follow README, open the console, and run the 10-minute demo. Resume copy matches what the app actually does.

## Definition of Done
CI + compose + docs + screenshots + Demo of the full script + Learning index of UI-00–08.

## Demo (full client script)
1. Open console, connect.
2. Collection Acme HR.
3. Upload text policy → READY.
4. Ask leave question → citations.
5. Glass box + page proof.
6. Unsupported question → abstain.
7. Delete → no ready docs.
8. (Optional) hosted generator paraphrase.

Timebox: 10 minutes. No terminal except if logs are part of the glass-box story.

## What I Must Be Able to Explain
What is production-shaped vs actually multi-tenant production. What you would still add (SSO, OCR, eval on real PDFs) and why it is not in V1.
