# Glass-Box Console — UI Product Spec

**Status:** Draft for review (no UI code until this spec is approved in the PR)  
**Date:** 2026-09-15  
**Audience:** Client demos and a resume-quality production-shaped console on top of Cited RAG Bot.

## 1. Problem

The API can ingest PDFs and return page-cited answers or a controlled no-answer. Clients and hiring managers will not curl. A chat box that only shows the final sentence throws away the system’s differentiator: **provenance**.

## 2. Product

An authenticated **glass-box console**:

1. Create and open a collection (no UUID pasting).
2. Upload a PDF and watch lifecycle until `READY` or `FAILED`.
3. Ask a question and see either a grounded answer with page citations or `INSUFFICIENT_EVIDENCE` with a reason.
4. Inspect the same request: pipeline stages, evidence `E1..En`, correlation id.
5. Open the cited PDF page.
6. Show delete and failure modes as first-class, not error toasts that vanish.

This is the product you demo. It is not a multi-tenant SaaS and not a public chatbot.

## 3. Non-goals (UI V1)

SSO, orgs, RBAC beyond one API key, OCR, citation repair, streaming tokens, mobile-native apps, marketing site, UI→database access.

## 4. Users

| User | What they need |
|---|---|
| You, in a client meeting | A browser on localhost (or later a URL) that survives a 10-minute script |
| Technical reviewer / resume | Visible pipeline, citations, fail-closed, tests |
| Future operator | Same console; hosted model via env |

## 5. Information architecture

```text
[ API key gate ]
    → Workspace
         → Collection list → Collection
              → Documents (ingest theater)
              → Ask (answer + citations)
              → Glass box (stages, evidence, correlation)
              → Page proof (PDF page)
              → Danger (delete)
```

Empty, loading, failed ingest, 401, 503, and abstain are designed states, not afterthoughts.

## 6. Existing API (do not break)

| Method | Path |
|---|---|
| GET | `/health`, `/ready` |
| POST | `/v1/collections` |
| GET | `/v1/collections/{id}` |
| POST | `/v1/collections/{id}/documents` |
| POST | `/v1/collections/{id}/documents/{document_id}/versions` |
| GET | `/v1/documents/{id}` |
| DELETE | `/v1/documents/{id}` |
| POST | `/v1/collections/{id}/query` |

Auth: `Authorization: Bearer <key>`. Default local key: `replace-me`.

## 7. New product APIs (thin, UI-owned)

Introduced in the phase that first needs them. Collection-scoped. Same auth.

| Phase | API | Purpose |
|---|---|---|
| UI-01 | `GET /v1/collections` | List collections for the principal |
| UI-02 | `GET /v1/collections/{id}/documents` | List documents + public ingestion status |
| UI-04 | `trace` on HTTP 200 query JSON (schema in `implementation/ui/ui-04-glass-box.md`) | Six `query.*` stages, request-scoped; evidence without `chunk_id` |
| UI-05 | `GET /v1/documents/{document_id}/content` | Full PDF bytes, Bearer, 1-based pages in the client |

Evidence text in trace is untrusted. Truncate per UI-04. Never treat as HTML.

## 8. Query UX contract

Map API fields 1:1. Do not rename status enums in the UI.

- `ANSWERED` → answer + citation chips (`document_name`, `page_start`–`page_end`)
- `INSUFFICIENT_EVIDENCE` → reason code (`NO_READY_DOCUMENTS`, `MODEL_ABSTENTION`, …) + explanation copy
- HTTP 401 → key gate
- HTTP 404 → not found (including cross-collection)
- HTTP 422 `citation_validation_failed` → fail-closed, not a guessed answer
- HTTP 503 `dense_retrieval_error` / `reranker_error` / `generation_provider_error` → outage, not abstain

## 9. Generation

- CI and default: `CITED_RAG_GENERATION_BACKEND=heuristic`
- UI-07: `openai_compatible` with base URL, model, API key in server settings (never shipped to the browser except “backend is hosted/heuristic”)
- Structured generation + citation validation stay mandatory

## 10. Tech stack

- `web/`: Vite, React, TypeScript, strict API types
- Tests: Vitest + Testing Library; Playwright smoke from UI-03
- Compose service `web`; browser origin separate from API; CORS already configured
- No Next.js in V1

## 11. Demo bar (every phase)

Each phase file has a **Demo** section. A phase is not `COMPLETE` until that demo runs on the phase branch without extra hidden setup.

Client-facing script (full product, after UI-08): 10 minutes — key → collection → upload → READY → question → citation → page → abstain → delete.

## 12. Resume one-liner (after UI-08)

“Production-shaped cited RAG console: collection-scoped PDF QA with application-owned page citations, visible retrieval/generation stages, and fail-closed no-answer — not a chat wrapper.”
