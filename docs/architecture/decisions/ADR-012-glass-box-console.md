# ADR-012 — Glass-Box Console (UI V1)

**Status:** Accepted  
**Date:** 2026-09-15  
**Extends:** ADR-011 (V1 locked policies). ADR-011 still wins on RAG, citations, auth, and fail-closed retrieval. Do not reopen ADR-012 locks without superseding this ADR.

## Context

Phases 00–23 delivered a PDF-only cited RAG **API**. There is no UI. Client demos and a resume need a product surface that shows *why* an answer is trusted, not a chatbot that hides ingest, evidence IDs, and no-answer.

V1 API gaps that block a console: no list-collections, no list-documents, no query-stage payload, no authenticated PDF fetch.

## Decision

Build a **glass-box product console**: one authenticated web app that can create collections, ingest PDFs, ask questions, and always show provenance (lifecycle, `E1..En`, page citations, abstention reasons, correlation id).

## Locked policies

1. **Package.** UI lives in repo-root `web/` (Vite + React + TypeScript). It is not inside `src/cited_rag/`. Python remains the API/worker package.

2. **API is the only backend.** The browser talks only to FastAPI `/v1/*`, `/health`, `/ready`. No Postgres, Redis, or Qdrant from the UI.

3. **Thin product APIs are allowed** and owned by UI phases that need them:
   - `GET /v1/collections`
   - `GET /v1/collections/{collection_id}/documents`
   - query **trace** on the HTTP 200 query body (schema locked in UI-04; ContextVar isolation, not the process-global `traces` buffer)
   - `GET /v1/documents/{document_id}/content` (full PDF bytes; UI-05)  
   Still collection-scoped. Still API-key auth. No architecture rewrite.

4. **Auth.** Same `Authorization: Bearer <api_key>` as the API. No SSO in UI V1. The console stores the key in `sessionStorage` (tab-scoped), never in repo, screenshots, or default logs.

5. **Untrusted PDF text.** Evidence and page text are data. Render as text nodes, never `innerHTML`. No “the PDF said to ignore instructions” path.

6. **Citations stay application-owned.** The UI must not invent page numbers. It displays only API-validated citations. No client-side citation repair.

7. **Fail-closed stays visible.** `503` operational errors and `200 INSUFFICIENT_EVIDENCE` are different screens/labels. Do not collapse them into “no results”.

8. **Generation.** Heuristic remains the default for tests and CI. A hosted OpenAI-compatible adapter is **UI-07**, behind `CITED_RAG_GENERATION_BACKEND`. Citation validation does not change.

9. **Compose.** Service `web` is part of the local/production-shaped stack from UI-00. CI compose-smoke must hit the UI origin by UI-08.

10. **Phasing.** One UI phase per branch/PR (`ui-00-foundation`, …). Do not implement later UI phases on an earlier branch. Demo script in each phase file is part of the Definition of Done.

## Alternatives rejected

| Alternative | Why not |
|---|---|
| Chat-only UI | Hides ingest, evidence IDs, no-answer, deletion. Weak resume and weak client trust story. |
| UI talking to Postgres/Qdrant | Bypasses the public contract. Bad architecture. |
| Next.js SSR | Unused for an authenticated console; more moving parts per phase. |
| Heuristic-only forever | Fine for unit tests; not a client Q&A product. |
| LLM before any UI | Mixes provider work with empty screens. |

## Consequences

- Backend list/trace/PDF routes are **product APIs**, not a new RAG design. They still need tests, collection scoping, and no secret logging.
- Screenshots and README demos must use a **text** PDF and a non-production API key placeholder.
- Hosted generation requires a real key in the operator’s `.env`; CI stays heuristic.
