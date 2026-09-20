# MEMORY — implementation handoff

This file is the **cold-start handoff** when the chat is cleared. It is not a transcript and not a substitute for ADRs.

Do not put secrets, API keys, or raw PDF text here.

## How to use

**Start of a session (before any code):**

1. Read this file, especially **Current state**.
2. Then follow `AGENTS.md` (ADR-011, current phase file, tests).
3. Do not start the next phase until the previous phase PR is merged to `main`, unless **Current state** says otherwise.

**When a phase is implemented, verified, and a PR is opened:**

1. Update **Current state**.
2. Append a **Phase record** using the template below. Fill every heading. If something was not done or not verified, say that explicitly.
3. Commit and push on the **phase branch** (never directly to `main`).
4. Only then is it safe to `/clear` the chat.

**Template for each phase record**

```text
### Phase XX — <name>
- Date:
- Branch:
- PR:
- Status in phase file:
- Goal (one paragraph):
- Files added/changed:
- Public contracts / commands:
- Decisions made in this phase (not already in ADR-011):
- Verification run (exact commands + results):
- Not verified / known gaps:
- Follow-ups for the next phase:
```

---

## Current state

| Field | Value |
|---|---|
| Last completed work | UI-07 hosted generation is `TESTED` and merged to `main` by PR [#40](https://github.com/pranjulya/cited-RAG-Bot/pull/40); UI-06 merged by PR #39. |
| Phase file status | Backend 00–23: **TESTED**. UI-00: `TESTED`; UI-01: `TESTED`; UI-02: `TESTED`; UI-03: `TESTED`; UI-04: `TESTED`; UI-05: `TESTED`; UI-06: `TESTED`; UI-07: `TESTED`; UI-08: `TESTED`. |
| Branch | `ui-08-production-pack` |
| PR | [#41](https://github.com/pranjulya/cited-RAG-Bot/pull/41) targets `main` (OPEN). |
| `main` | `a8c4aa0` — merged UI-07 via PR #40. **Do not push or merge to `main` except via PR.** |
| Next action | Review and merge #41. UI-08 is the final planned UI phase. |
| Blockers | No OCR. Live Docker/Compose verification was unavailable in this environment; CI retains those checks. |

---

## Standing rules (do not rediscover)

- V1 architecture is frozen in `docs/architecture/decisions/ADR-011-v1-locked-policies.md`. If docs disagree, **ADR-011 wins**.
- Package root is `src/cited_rag/`. Do not use a top-level `src/api` tree.
- One implementation phase at a time. No opportunistic future-phase code.
- Git: **never commit, push, or merge directly to `main`**. One branch per phase/feature/fix; land through a PR. See `AGENTS.md` Git Workflow.
- `gh` token needs `workflow` scope to push `.github/workflows/*`. Refresh: `gh auth refresh --hostname github.com -s workflow,repo`.
- Ignore untracked `.commandcode/` (local tooling, not part of the product).
- Do not continue the old Codex worktree `phase-00-foundation` work; this repo’s `phase-00-foundation` branch is the real one.

---

## Phase records (historical snapshots)

The entries below were written when each phase PR was **opened** and are kept as snapshots. Where a value has changed since, the record says so inline (for example `OPEN when written; now MERGED`). No record below is the live status.

**Authoritative now:** Current state (above) and the `**Status:**` line in the current backend/UI phase file (**TESTED** on `main`, not REVIEWED, not COMPLETE).

### UI-08 — Production Pack
- **Date:** 2026-09-20
- **Branch:** `ui-08-production-pack`
- **PR:** [#41](https://github.com/pranjulya/cited-RAG-Bot/pull/41) into `main` (OPEN)
- **Status in phase file:** `TESTED`
- **Goal:** Package the glass-box console as a production-shaped demo with a tested static web image contract, browser smoke coverage, responsive presentation, Compose/CI checks, screenshot evidence, and operator/demo documentation without adding new RAG behavior.
- **Files added/changed:** `.github/workflows/ci.yml`, `.gitignore`, `web/package.json`, `web/package-lock.json`, `web/playwright.config.ts`, `web/tests/smoke.spec.ts`, `web/src/styles.css`, `web/vite.config.ts`, `docs/screenshots/ui-08-ask-narrow.png`, `README.md`, `docs/operations/deployment.md`, `Learning/ui-08-production-pack.md`, `Learning/README.md`, UI-08 status/readme, hosted-response type guard/test, and the implementation plan.
- **Public contracts / commands:** Added `npm run test:e2e` (Playwright Chromium smoke); CI now runs the production web build and browser smoke with API route mocks, while Compose continues to probe `http://localhost:8080/` alongside API health/readiness. No API or citation contract changed.
- **Decisions made in this phase (not already in ADR-011):** Browser smoke uses deterministic API mocks to avoid billed provider calls; the web image remains Vite build output served by nginx; the hosted adapter validates the response shape explicitly so current mypy versions keep CI fail-closed.
- **Verification run (exact commands + results):** `npm ci` — passed; `npm test -- --run` — 19 passed; `npm run build` — passed; `env PLAYWRIGHT_CHANNEL=chrome npm run test:e2e -- --project=chromium` — 1 passed; `/private/tmp/cited-rag-ui-05-page-proof/.venv/bin/ruff check .` — passed; `/private/tmp/cited-rag-ui-05-page-proof/.venv/bin/ruff format --check .` — passed; `/private/tmp/cited-rag-ui-05-page-proof/.venv/bin/mypy src` — passed; `/private/tmp/cited-rag-ui-05-page-proof/.venv/bin/pytest tests/unit -q` — 228 passed, 1 skipped; `docker compose config` — passed; `git diff --check` — passed.
- **Not verified / known gaps:** Local Docker daemon/image build and live Compose/client demo were unavailable; CI runs the full Docker/Compose checks. No manual browser run against a live API or hosted provider was performed.
- **Follow-ups for the next phase:** Merge #41; no further UI implementation phase is planned after UI-08. Future work requires a new phase/ADR for SSO, OCR, or real multi-tenant deployment.

### UI-07 — Hosted Generation
- **Date:** 2026-09-20
- **Branch:** `ui-07-hosted-generation`
- **PR:** [#40](https://github.com/pranjulya/cited-RAG-Bot/pull/40) into `main` (OPEN)
- **Status in phase file:** `TESTED`
- **Goal:** Add an OpenAI-compatible grounded-generation adapter while keeping heuristic generation as the CI default and preserving the existing evidence/citation contract.
- **Files added/changed:** `src/cited_rag/adapters/generation/openai_compatible.py`, generation settings/factory, query response metadata, `web/src/App.tsx`, frontend/backend tests, `.env.example`, deployment/README docs, `Learning/ui-07-hosted-generation.md`, Learning index, phase status, and this handoff.
- **Public contracts / commands:** `CITED_RAG_GENERATION_BACKEND=heuristic|openai_compatible`; hosted settings remain server-side (`BASE_URL`, `MODEL`, `API_KEY`). Query 200 responses add non-secret `generation_backend`; the UI renders `heuristic` or `hosted` only.
- **Decisions made in this phase (not already in ADR-011):** The adapter uses stdlib HTTP and JSON-mode chat completions, appending `/chat/completions` to an OpenAI-compatible `/v1` base URL; missing hosted keys fail startup rather than silently falling back; provider metadata is exposed only as a backend label.
- **Verification run (exact commands + results):** `/private/tmp/cited-rag-ui-05-page-proof/.venv/bin/pytest tests/unit -q` — 227 passed, 1 skipped; `/private/tmp/cited-rag-ui-05-page-proof/.venv/bin/pytest tests/integration/test_query_api.py -q` — 2 skipped because no database is configured; `npm test -- --run` — 19 passed; `npm run build` — passed; `/private/tmp/cited-rag-ui-05-page-proof/.venv/bin/ruff check src tests` — passed; `/private/tmp/cited-rag-ui-05-page-proof/.venv/bin/mypy` — passed; `git -c core.fsmonitor=false diff --check` — passed.
- **Not verified / known gaps:** No live billed provider call, live Compose hosted demo, Postgres integration, or manual browser run was performed; fake transport fixtures cover success, malformed JSON, timeout, and missing evidence IDs.
- **Follow-ups for the next phase:** Merge #40 before starting UI-08; keep the hosted key server-only while packaging compose/CI/screenshots/deploy evidence.

### UI-06 — Fail-Closed Studio
- **Date:** 2026-09-20
- **Branch:** `ui-06-fail-closed-studio`
- **PR:** [#39](https://github.com/pranjulya/cited-RAG-Bot/pull/39) into `main` (OPEN when written; now MERGED `a1370da`)
- **Status in phase file:** `TESTED`
- **Goal:** Make failure modes demoable with distinct abstain/outage/auth/not-found/citation-validation states, visible ingestion failure codes, and a confirmed delete flow that waits for the authoritative 404.
- **Files added/changed:** `web/src/App.tsx`, `web/src/App.test.tsx`, `implementation/ui/ui-06-fail-closed-studio.md`, `Learning/ui-06-fail-closed-studio.md`, `Learning/README.md`, and this handoff.
- **Public contracts / commands:** No API changes. The UI uses existing `DELETE /v1/documents/{document_id}` and polls `GET /v1/documents/{document_id}` until 404; 503 failure codes remain visible separately from the outage copy.
- **Decisions made in this phase (not already in ADR-011):** Deletion removes a row only after the server reports 404; failure codes are links to in-console anchors; the optional scenario panel was skipped because the existing states and demo flow cover the phase.
- **Verification run (exact commands + results):** `npm test -- --run` — 18 passed; `npm run build` — passed; `/private/tmp/cited-rag-ui-05-page-proof/.venv/bin/ruff check src tests` — passed; `/private/tmp/cited-rag-ui-05-page-proof/.venv/bin/mypy` — passed; `/private/tmp/cited-rag-ui-05-page-proof/.venv/bin/pytest tests/unit -q` — 221 passed, 1 skipped; `git -c core.fsmonitor=false diff --check` — passed.
- **Not verified / known gaps:** Live Compose failure/delete demo, Postgres integration tests, and manual browser interaction were not run in this sandbox.
- **Follow-ups for the next phase:** Merge #39 before starting UI-07; preserve the visible fail-closed distinction while adding the hosted generation adapter.

### UI-05 — Page Proof
- **Date:** 2026-09-20
- **Branch:** `ui-05-page-proof`
- **PR:** [#37](https://github.com/pranjulya/cited-RAG-Bot/pull/37) into `main` (OPEN when written; now MERGED `fedfdab`)
- **Status in phase file:** `TESTED`
- **Goal:** Let users click a validated citation, fetch the source PDF through the authenticated API, and open its parser-owned 1-based page in the browser viewer.
- **Files added/changed:** Authenticated document-content route, route/integration/unit tests, citation viewer UI/tests/styles, `Learning/ui-05-page-proof.md`, Learning index, phase status, and this handoff.
- **Public contracts / commands:** `GET /v1/documents/{document_id}/content` returns raw `application/pdf` bytes with `Cache-Control: private, no-store`; unauthorized/missing/deleted documents return 404, storage failure returns 503, and oversized bytes return 413. The UI sends Bearer auth and uses `#page=<page_start>`.
- **Decisions made in this phase (not already in ADR-011):** The API derives the canonical source key instead of exposing `storage_uri`; the native PDF viewer replaces a new pdf.js dependency while preserving the API's 1-based page authority.
- **Verification run (exact commands + results):** `./.venv/bin/ruff check src tests` — passed; `./.venv/bin/mypy` — passed; `./.venv/bin/pytest tests/unit -q` — 221 passed, 1 skipped; `./.venv/bin/pytest tests/integration/test_upload.py -q` — 11 skipped because no database is configured; `npm test -- --run` — 14 passed; `npm run build` — passed; `git diff --check` — passed.
- **Not verified / known gaps:** Postgres-backed integration and live Compose/browser demo require external services unavailable in this environment.
- **Follow-ups for the next phase:** Merge #37 before starting UI-06; preserve the 404-vs-503 distinction when adding fail-closed studio states.

### UI-04 — Glass Box
- **Date:** 2026-09-20
- **Branch:** `ui-04-glass-box`
- **PR:** [#35](https://github.com/pranjulya/cited-RAG-Bot/pull/35) into `main` (OPEN when written; now MERGED)
- **Status in phase file:** `TESTED`
- **Goal:** Add a request-scoped query trace to every HTTP 200 response so the console shows the six locked stages, bounded `E1..En` evidence, timings, and correlation id without mixing concurrent requests.
- **Files added/changed:** Query trace response models/route, ContextVar tracing, query evidence propagation, trace settings and tests, `web/src/App.tsx`, `web/src/App.test.tsx`, `web/src/styles.css`, `Learning/ui-04-glass-box.md`, Learning index, phase status, and this handoff.
- **Public contracts / commands:** `QueryResponse.trace` is required on 200 responses and contains six ordered stage rows plus bounded evidence text. 503 responses remain detail-only. `CITED_RAG_TRACE_EVIDENCE_CHARS` controls per-item text truncation (default 2000).
- **Decisions made in this phase (not already in ADR-011):** Product traces use a task-local ContextVar buffer while retaining the process-global list for legacy log/metric tests; skipped stages are explicit rows so early exits remain inspectable; evidence is rendered as text nodes.
- **Verification run (exact commands + results):** `UV_CACHE_DIR=/private/tmp/cited-rag-uv-cache uv run --extra dev ruff check src tests` — passed; `UV_CACHE_DIR=/private/tmp/cited-rag-uv-cache uv run --extra dev mypy` — passed; `UV_CACHE_DIR=/private/tmp/cited-rag-uv-cache uv run --extra dev pytest tests/unit -q` — 218 passed, 1 skipped; `npm test -- --run` — 13 passed; `npm run build` — passed; `git diff --check` — passed.
- **Not verified / known gaps:** Postgres integration tests and the Docker/Compose demo were not run because the local Docker daemon was unavailable; manual browser interaction was not run from this sandbox.
- **Follow-ups for the next phase:** Merge #35 before starting UI-05; use the trace evidence IDs and validated citations as the input to page-proof navigation.

### UI-03 — Ask + Citations
- **Date:** 2026-09-20
- **Branch:** `ui-03-ask-citations`
- **PR:** [#34](https://github.com/pranjulya/cited-RAG-Bot/pull/34) into `main` (OPEN when written; now MERGED)
- **Status in phase file:** `TESTED`
- **Goal:** Let a user ask a collection-scoped question and see an answer with validated page citations, or a first-class insufficient-evidence result.
- **Files added/changed:** `web/src/App.tsx`, `web/src/App.test.tsx`, `Learning/ui-03-ask-citations.md`, Learning index, phase status, and this handoff.
- **Public contracts / commands:** The console posts `{question}` to `POST /v1/collections/{collection_id}/query`; `ANSWERED` renders answer/citations/request id, `INSUFFICIENT_EVIDENCE` renders reason without answer text, `503` renders outage, and `413` renders query-too-long.
- **Decisions made in this phase (not already in ADR-011):** Citation chips display `document_name` plus the inclusive page range; request results and errors are ignored after collection navigation so one collection cannot paint another collection's screen.
- **Verification run (exact commands + results):** `UV_CACHE_DIR=/private/tmp/cited-rag-uv-cache uv run --extra dev ruff check src tests` — passed; `UV_CACHE_DIR=/private/tmp/cited-rag-uv-cache uv run --extra dev mypy` — passed; `UV_CACHE_DIR=/private/tmp/cited-rag-uv-cache uv run --extra dev pytest tests/unit` — 215 passed, 1 skipped; `npm test -- --run` — 12 passed; `npm run build` — passed. Independent review found no remaining P0/P1 issues; review P2 state-isolation fixes were applied and re-tested.
- **Not verified / known gaps:** Isolated live Compose query demo was attempted but the local Docker daemon was unresponsive; UI behavior is covered by Vitest and the existing query API/unit tests. Manual browser interaction was not run from this sandbox.
- **Follow-ups for the next phase:** Merge #34 before starting UI-04; preserve the public citation shape and keep stage/E-ID trace work in UI-04.

### UI-02 — Ingest Theater
- **Date:** 2026-09-18
- **Branch:** `ui-02-ingest-theater`
- **PR:** [#33](https://github.com/pranjulya/cited-RAG-Bot/pull/33) into `main` (MERGED)
- **Status in phase file:** `TESTED`
- **Goal:** Let a user upload a PDF to the open collection and see the authoritative ingest lifecycle through `READY` or a public `FAILED` code.
- **Files added/changed:** `src/cited_rag/ports/repositories.py`, PostgreSQL document repository, document routes and API tests, `web/src/App.tsx` and browser tests, `Learning/ui-02-ingest-theater.md`, Learning index, phase status, and this handoff.
- **Public contracts / commands:** `GET /v1/collections/{collection_id}/documents` returns only a principal-owned collection's documents and current version status. The UI uploads multipart PDFs, polls the existing document endpoint, bounds waiting status, and shows a versioned table.
- **Decisions made in this phase (not already in ADR-011):** Poll every second for at most 61 status reads, then show a waiting message. Browser request/poll updates are scoped to the currently open collection so navigation cannot display another collection's status.
- **Verification run (exact commands + results):** `UV_CACHE_DIR=/private/tmp/cited-rag-uv-cache uv run --extra dev ruff check src tests` — passed; `UV_CACHE_DIR=/private/tmp/cited-rag-uv-cache uv run --extra dev mypy` — passed; `UV_CACHE_DIR=/private/tmp/cited-rag-uv-cache uv run --extra dev pytest tests/unit` — 215 passed, 1 skipped; `npm test -- --run` — 8 passed; `npm run build` — passed. Isolated Compose demo uploaded a text PDF, observed `QUEUED`, then `READY`, and returned it from the collection document list. Independent review found and resolved collection-navigation races, non-OK status retry, and the versioned-table requirement.
- **Not verified / known gaps:** Manual browser interaction on the Docker host was not run from this sandbox; Vitest covers browser behavior. A live failed scan was not rerun; backend/UI tests cover `PDF_UNSUPPORTED` rendering.
- **Follow-ups for the next phase:** Merge #33 before starting UI-03; retain collection-scoped status polling as the status source until a later realtime phase explicitly replaces it.

### UI-01 — Collections
- **Date:** 2026-09-18
- **Branch:** `ui-01-collections`
- **PR:** [#32](https://github.com/pranjulya/cited-RAG-Bot/pull/32) into `main` (MERGED `d2ed797`)
- **Status in phase file:** `TESTED`
- **Goal:** Let a console user create and list their collections without copying UUIDs, while keeping list visibility scoped to the authenticated API principal.
- **Files added/changed:** `src/cited_rag/ports/repositories.py`, PostgreSQL collection repository, collection route, API/persistence tests, `web/src/App.tsx`, browser tests/setup, `Learning/ui-01-collections.md`, Learning index, phase status, and this handoff.
- **Public contracts / commands:** `GET /v1/collections` returns the authenticated principal's collection id, name, and status. The console creates a collection with the existing POST, lists it, and opens `/collections/{collection_id}`.
- **Decisions made in this phase (not already in ADR-011):** List order is creation order. The small console uses the browser History API instead of adding a router dependency for one collection shell.
- **Verification run (exact commands + results):** `UV_CACHE_DIR=/private/tmp/cited-rag-uv-cache uv run --extra dev pytest tests/unit` — 213 passed, 1 skipped; `UV_CACHE_DIR=/private/tmp/cited-rag-uv-cache uv run --extra dev ruff check src tests` — passed; `UV_CACHE_DIR=/private/tmp/cited-rag-uv-cache uv run --extra dev mypy` — passed; `npm test -- --run` — 6 passed; `npm run build` — passed. Isolated Compose cold start with alternate host ports completed with all services healthy; in-container API create/list returned `Acme HR policies`.
- **Not verified / known gaps:** Manual browser interaction on the Docker host was not run from this sandbox; browser behavior is covered by Vitest. Postgres integration tests require the integration environment and were not separately run, though the compose stack applied migrations and the live API create/list demo succeeded.
- **Follow-ups for the next phase:** After #32 merges, start UI-02 only: collection-scoped document list, PDF upload, and terminal-status polling.

### Phase 23 — Documentation, Learning, and Interview Readiness
- **Date:** 2026-09-09
- **Branch:** `phase-23-docs-learning`
- **PR:** [#28](https://github.com/pranjulya/cited-RAG-Bot/pull/28)
- **Status in phase file:** `TESTED`
- **Goal:** README, Learning index, interview Q&A, and a reproducible golden-v1 benchmark table so a reviewer can run the project and see measured dense/sparse/hybrid/rerank scores.
- **Files added/changed:** `README.md`, `reports/v1-defaults.md`, `Learning/20-rag-quality-experiments.md`, `Learning/23-documentation-learning.md`, `src/cited_rag/evaluation/__main__.py` (`--matrix`), `src/cited_rag/evaluation/experiments.py`, `evaluation/results/matrix.json`.
- **Public contracts / commands:** `python -m cited_rag.evaluation`; `python -m cited_rag.evaluation --matrix`.
- **Verification:** evaluation CLI + unit tests on this branch (see commit). Live compose smoke is in CI, not re-run locally here.
- **Not verified:** hosted encoder/reranker; live Postgres/Qdrant E2E.
- **Follow-ups:** Review/merge #14–#28 in order. Do not start the glass-box UI until that lands.

### Phase 15 — End-to-End Query API
- **Date:** 2026-09-09
- **Branch:** `phase-15-query-api`
- **PR:** [#20](https://github.com/pranjulya/cited-RAG-Bot/pull/20)
- **Status in phase file:** `IN_PROGRESS` when written; now `TESTED`
- **Goal:** Public `POST /v1/collections/{collection_id}/query` runs the full grounded pipeline.
- **Verification:** `pytest tests/unit` **165 passed**, 1 skipped. Integration query tests not run locally.
- **Follow-ups:** Phase 16 deletion; hosted LLM adapter; persist QueryRun completion.

### Phase 14 — No-Answer Policy
- **PR:** [#19](https://github.com/pranjulya/cited-RAG-Bot/pull/19)
- **Goal:** Distinguish abstention reasons from infrastructure errors.

### Phase 13 — Citation Validation
- **PR:** [#18](https://github.com/pranjulya/cited-RAG-Bot/pull/18)
- **Goal:** Fail closed on unapproved evidence IDs; public citations omit `chunk_id`.

### Phase 12 — Grounded Generation
- **PR:** [#17](https://github.com/pranjulya/cited-RAG-Bot/pull/17)
- **Goal:** Evidence-only structured generation; PDF text is untrusted.

### Phase 11 — Context Builder
- **PR:** [#16](https://github.com/pranjulya/cited-RAG-Bot/pull/16)
- **Goal:** Assign `E1..En`; model sees ID + text only.

### Phase 10 — Reranking

- **Date:** 2026-09-09
- **Branch:** `phase-10-reranking`
- **PR:** [#15](https://github.com/pranjulya/cited-RAG-Bot/pull/15) (`phase-10-reranking` → `phase-09-hybrid-rrf`; OPEN when written, now MERGED)
- **Status in phase file:** `IN_PROGRESS` when written; now `TESTED`
- **Goal:** Rerank fused candidates through a replaceable port; production timeout/failure is `RERANKER_ERROR`; evaluation may disable rerank.

- **Files added/changed:**
  - `ports/reranker.py`
  - `adapters/rerank/overlap.py` — deterministic lexical overlap
  - `application/rerank.py` — timeout wrapper, evaluation passthrough
  - `RerankedEvidence`, `RerankerError`
  - `EvaluationRunConfig.include_rerank`
  - Settings: `CITED_RAG_RERANKER_BACKEND`, `CITED_RAG_RERANK_TOP_N`, `CITED_RAG_RERANKER_TIMEOUT_SECONDS`
  - Tests: `tests/unit/test_rerank.py`
  - `Learning/10-reranking.md`

- **Public contracts / commands:**
  - `rerank_candidates(query, fused, reranker=, top_n=, timeout_seconds=)`
  - Empty input → empty output
  - Timeout / provider error → `RERANKER_ERROR` (no fused-order fallback)
  - `EvaluationRunConfig(include_rerank=False)` keeps fused order with `reranker_name=disabled`

- **Decisions made in this phase (not already in ADR-011):**
  - Default adapter is lexical overlap so CI does not download a cross-encoder. Production can swap a cross-encoder behind the same port.

- **Verification run (exact commands + results):**
  - ruff / mypy — passed
  - `pytest tests/unit` — **135 passed, 1 skipped**

- **Not verified / known gaps:**
  - Hosted/local cross-encoder quality vs overlap
  - Query API wiring (Phase 15)

- **Follow-ups for the next phase:**
  - Phase 11: context builder and request-scoped evidence IDs (`E1`, `E2`, …)

### Phase 09 — Hybrid Retrieval and RRF

- **Date:** 2026-09-09
- **Branch:** `phase-09-hybrid-rrf`
- **PR:** [#14](https://github.com/pranjulya/cited-RAG-Bot/pull/14) (`phase-09-hybrid-rrf` → `main`; OPEN when written, now MERGED)
- **Status in phase file:** `IN_PROGRESS` when written; now `TESTED`
- **Goal:** Run dense and sparse independently, fuse with in-process RRF, preserve source ranks, fail closed on retriever errors, fuse empty hit lists.

- **Files added/changed:**
  - `application/retrieval/` package: `retrievers.py`, `fusion.py` (`FusionStrategy`, `ReciprocalRankFusion`), `hybrid.py`
  - `domain/models/retrieval.py` — `FusedCandidate`
  - `domain/models/evaluation.py` — `EvaluationRunConfig` (ablations only)
  - `HybridFusionError` for invalid ranks / duplicate metadata conflict
  - Settings: `CITED_RAG_RRF_K`, `CITED_RAG_FUSED_TOP_K`
  - Tests: `tests/unit/test_hybrid_rrf.py`, `tests/integration/test_hybrid_retrieval.py`
  - `Learning/09-hybrid-retrieval-rrf.md`

- **Public contracts / commands:**
  - `retrieve_hybrid(...)` always runs both retrievers unless `EvaluationRunConfig` disables a side
  - Empty list from one retriever still fuses
  - Operational dense/sparse failure propagates (`DENSE_RETRIEVAL_ERROR` / `SPARSE_RETRIEVAL_ERROR`)
  - RRF score is rank-only: `Σ 1/(k + rank)`

- **Decisions made in this phase (not already in ADR-011):**
  - Tie-break fused order by `chunk_id` string
  - Duplicate chunk_id in one list keeps the best (lowest) rank
  - Duplicate chunk with conflicting provenance fails fusion

- **Verification run (exact commands + results):**
  - ruff / mypy — passed
  - `pytest tests/unit` — **127 passed, 1 skipped**
  - `pytest tests/integration` — **not run locally**

- **Not verified / known gaps:**
  - Live Qdrant hybrid search
  - Query API orchestration (Phase 15)

- **Follow-ups for the next phase:**
  - Phase 10: rerank fused candidates; production timeout is `RERANKER_ERROR`

### Phase 08 — Dense Retrieval

- **Date:** 2026-09-08
- **Branch:** `phase-08-dense-retrieval`
- **PR:** [#13](https://github.com/pranjulya/cited-RAG-Bot/pull/13) (`phase-08-dense-retrieval` → `main`, MERGED `b6d7774`)
- **Status in phase file:** `IN_PROGRESS` when written; now `TESTED`
- **Goal:** Collection-scoped dense retrieval over READY version ids with fail-closed payload validation.

- **Follow-ups for the next phase:**
  - Phase 09 hybrid RRF (opened as #14)

### Phase 07 — Sparse Indexing and Retrieval

- **Date:** 2026-09-08
- **Branch:** `phase-07-sparse-indexing-retrieval`
- **PR:** [#12](https://github.com/pranjulya/cited-RAG-Bot/pull/12) (`phase-07-sparse-indexing-retrieval` → `main`, MERGED `b9ec137`)
- **Status in phase file:** `IN_PROGRESS` when written; now `TESTED`
- **Goal:** Encode sparse vectors onto the same chunk UUIDs as dense, retrieve with collection + version filters, and set `READY` only after both named vectors exist.

- **Files added/changed:**
  - `ports/sparse_encoder.py`; store `upsert_sparse` / `search_sparse`
  - `adapters/sparse/lexical.py` (default tests/dev); `fastembed_bm42.py` optional extra
  - `application/indexing.py` — sparse upsert, completeness check, `finalize_ready`
  - `application/retrieval.py` — sparse `RetrievedCandidate` list
  - Migration `0004_sparse_encoder_config`
  - Worker/ingestion: dense then sparse then READY
  - Tests: `tests/unit/test_sparse.py`; ingestion tests now expect READY
  - `Learning/07-sparse-indexing-retrieval.md`

- **Public contracts / commands:**
  - `CITED_RAG_SPARSE_ENCODER_BACKEND` (`lexical` default, `bm42` optional)
  - `CITED_RAG_SPARSE_ENCODER_NAME`, `CITED_RAG_SPARSE_ENCODER_VERSION`
  - Sparse updates the same Qdrant point; does not replace dense
  - Production search uses `collection_id` and `document_version_id IN (active READY versions)`
  - Empty READY set returns no hits

- **Decisions made in this phase (not already in ADR-011):**
  - Default encoder is lexical TF so CI does not download BM42; production V1 adapter is FastEmbed BM42 via settings
  - Sparse is applied with `update_vectors` so dense is not wiped

- **Verification run (exact commands + results):**
  - ruff / mypy — passed
  - `pytest tests/unit` — **90 passed, 1 skipped**
  - `pytest tests/integration` — **not run locally**

- **Not verified / known gaps:**
  - Live Qdrant sparse search / READY path
  - FastEmbed BM42 model download and encoding
  - Dense retrieval product path (Phase 08); RRF (Phase 09)

- **Follow-ups for the next phase:**
  - Confirm CI integration
  - Phase 08: collection-scoped dense retrieval on READY versions

### Phase 06 — Embedding and Dense Indexing

- **Date:** 2026-09-07
- **Branch:** `phase-06-dense-indexing`
- **PR:** [#11](https://github.com/pranjulya/cited-RAG-Bot/pull/11) (`phase-06-dense-indexing` → `main`, MERGED `2a87918`)
- **Status in phase file:** `IN_PROGRESS` when written; now `TESTED`
- **Goal:** Embed persisted chunks and upsert dense named vectors on chunk UUIDs in one application Qdrant collection that already declares `sparse`. Never `READY`. No sparse values.

- **Files added/changed:**
  - `ports/embedding.py`, `ports/retrieval_store.py`
  - `domain/embedding.py`, `domain/indexing.py`
  - `adapters/embedding/hashing.py` — deterministic test/dev backend
  - `adapters/retrieval/qdrant.py`, `adapters/retrieval/memory.py`
  - `application/indexing.py` — batch embed + dense upsert
  - Worker/ingestion: parse, chunk, dense index
  - Compose/CI: Qdrant service; `/ready` probes Qdrant when configured
  - Tests: `tests/unit/test_embedding.py`, `tests/unit/test_dense_index.py`, `tests/integration/test_dense_indexing.py`
  - `Learning/06-dense-indexing.md`

- **Public contracts / commands:**
  - `CITED_RAG_QDRANT_URL`, `CITED_RAG_QDRANT_COLLECTION` (default `cited_rag`)
  - `CITED_RAG_EMBEDDING_BACKEND` (`hash`), `CITED_RAG_EMBEDDING_MODEL`, `CITED_RAG_EMBEDDING_DIMENSION` (default 32), `CITED_RAG_EMBEDDING_BATCH_SIZE`, `CITED_RAG_INDEX_VERSION`
  - Named vectors `dense` and `sparse` on the same point; this phase writes `dense` only
  - Point id = chunk UUID

- **Decisions made in this phase (not already in ADR-011):**
  - Default embedder is a normalized hash vector so tests/dev do not need a hosted model
  - Authoritative chunk text stays out of Qdrant payload

- **Verification run (exact commands + results):**
  - ruff / mypy — passed
  - `pytest tests/unit` — **82 passed, 1 skipped**
  - `pytest tests/integration` — **not run locally** (Docker/Qdrant did not start)

- **Not verified / known gaps:**
  - Live Qdrant upsert/payload-index/idempotent replay
  - Hosted embedding adapters
  - Sparse vectors and `READY` (Phase 07)

- **Follow-ups for the next phase:**
  - Confirm CI integration job with Qdrant
  - Phase 07: sparse upserts on the same points + finalize `READY`

### Phase 05 — Provenance-Aware Chunking

- **Date:** 2026-09-07
- **Branch:** `phase-05-provenance-aware-chunking`
- **PR:** [#10](https://github.com/pranjulya/cited-RAG-Bot/pull/10) (`phase-05-provenance-aware-chunking` → `main`, MERGED `97dff92`)
- **Status in phase file:** `TESTED`
- **Goal:** Split parsed pages into ordered chunks with deterministic UUIDv5 identities and explicit page ranges. Never `READY`. No embeddings.

- **Files added/changed:**
  - `ports/chunker.py`, `domain/chunking.py` (`ChunkingConfig`)
  - `adapters/chunking/page_window.py` — single-page character windows + overlap
  - `application/chunking.py` — persist; skip if chunks already exist
  - Worker/ingestion pipeline: parse then chunk
  - Settings: `chunk_target_chars`, `chunk_overlap_chars`
  - Tests: `tests/unit/test_chunker.py`, `tests/integration/test_chunking.py`
  - `Learning/05-provenance-aware-chunking.md`

- **Public contracts / commands:**
  - `CITED_RAG_CHUNK_TARGET_CHARS` (default 1200), `CITED_RAG_CHUNK_OVERLAP_CHARS` (default 200, must be smaller than target)
  - Strategy name `page_char_split_v1`
  - Chunk `page_start`/`page_end` are the source PDF page; V1 does not merge pages
  - Chunk id = UUIDv5 from version, page range, order, content hash

- **Decisions made in this phase (not already in ADR-011):**
  - Character windows, not tokens; `token_count` is whitespace-split length
  - Empty pages produce no chunks; zero chunks after parse is `PDF_UNSUPPORTED`
  - `document_versions.chunking_config` JSONB stores strategy/target/overlap used for that version

- **Verification run (exact commands + results):**
  - ruff / mypy — passed
  - `pytest tests/unit` — **70 passed, 1 skipped**
  - `pytest tests/integration` — **37 passed**

- **Not verified / known gaps:**
  - Semantic/cross-page chunking not implemented
  - No dense/sparse index; version stays `PROCESSING`

- **Follow-ups for the next phase:**
  - Review/merge [PR #10](https://github.com/pranjulya/cited-RAG-Bot/pull/10)
  - Phase 06: embedding + dense indexing. New branch from merged `main`.

### Phase 04 — PDF Parsing and Page Provenance

- **Date:** 2026-09-07
- **Branch:** `phase-04-pdf-parsing-provenance`
- **PR:** [#9](https://github.com/pranjulya/cited-RAG-Bot/pull/9) (`phase-04-pdf-parsing-provenance` → `main`, MERGED `51bd34a`)
- **Status in phase file:** `TESTED`
- **Goal:** Parse retained PDFs into ordered pages with original page numbers, persist provenance, classify corrupt/password/empty extraction. Never `READY`. No chunking.

- **Files added/changed:**
  - `src/cited_rag/ports/parser.py`, `domain/parser.py` (`ParsedPage`, normalize)
  - `adapters/parser/` — preflight, `PypdfDocumentParser`, `DoclingDocumentParser`, factory
  - `application/parsing.py`, worker loads storage + parser
  - Version `set_page_count`; parser exceptions + failure codes
  - Settings: `CITED_RAG_PARSER_BACKEND` (`pypdf` default; `docling` via extra)
  - Tests: `tests/unit/test_parser.py`, `tests/integration/test_parsing.py`, `tests/pdf_fixtures.py`
  - `Learning/04-pdf-parsing-provenance.md`

- **Public contracts / commands:**
  - Worker parse: load source PDF → `DocumentParser.parse` → `pages` rows + `page_count`
  - Version remains `PROCESSING` (not `READY`)
  - Failures: `PDF_PARSE_FAILED`, `PDF_PASSWORD_PROTECTED`, `PDF_UNSUPPORTED`
  - `pip install 'cited-rag[parser]'` then `CITED_RAG_PARSER_BACKEND=docling`

- **Decisions made in this phase (not already in ADR-011):**
  - Default backend is `pypdf` so CI/Compose do not download Docling layout models.
  - pypdf preflight classifies password/corrupt before either backend extracts text.
  - Empty extractable text is unsupported, not an empty page index.

- **Verification run (exact commands + results):**
  - `.venv/bin/ruff check .` / `ruff format --check` / `mypy src` — passed
  - `.venv/bin/pytest tests/unit` — **57 passed, 1 skipped** (Docling extra)
  - `CITED_RAG_DATABASE_URL=postgresql+asyncpg://…/cited_rag_test pytest tests/integration` — **34 passed**

- **Not verified / known gaps:**
  - Docling adapter contract test skipped unless `docling` is installed
  - Live Docker upload→worker→pages not executed
  - No chunking, embeddings, or `READY`

- **Follow-ups for the next phase:**
  - Review/merge [PR #9](https://github.com/pranjulya/cited-RAG-Bot/pull/9)
  - Phase 05: provenance-aware chunking. New branch from merged `main`.

### Phase 03 — Asynchronous Ingestion Worker

- **Date:** 2026-09-07
- **Branch:** `phase-03-async-ingestion`
- **PR:** [#6](https://github.com/pranjulya/cited-RAG-Bot/pull/6) (`phase-03-async-ingestion` → `main`, MERGED `f91e47f`)
- **Status in phase file:** `REVIEWED` when written; now `TESTED` on `main`, not `COMPLETE`
- **Goal:** Move ingestion off the HTTP request: durable Postgres job + Redis/arq wake-up, `QUEUED → PROCESSING`, never `READY`. Stub later pipeline stages.

- **Files added/changed:**
  - `src/cited_rag/ports/queue.py`, `adapters/queue/arq_redis.py`, `adapters/queue/memory.py` (test-only)
  - `src/cited_rag/application/ingestion.py`, `workers/ingestion_worker.py`
  - `application/upload.py` — commit `QUEUED+PENDING` then Redis publish; no compensate-delete after owned storage
  - `adapters/persistence/postgres/repositories.py` — atomic `claim` (`UPDATE … RETURNING`)
  - Settings: `CITED_RAG_REDIS_URL`, `ingestion_max_attempts`, `ingestion_lease_seconds`; production requires DB + Redis
  - `/ready` — DB, local storage, Redis ping when configured
  - `docker-compose.yml` — redis, migrate, worker
  - CI `integration-postgres` includes Redis service + `CITED_RAG_REDIS_URL`
  - Tests: `tests/unit/test_memory_queue.py`, `tests/integration/test_ingestion.py`
  - `Learning/03-async-ingestion.md`

- **Public contracts / commands:**
  - Upload still `202` `QUEUED`; worker owns `QUEUED → PROCESSING`
  - Durable queue: Postgres `QUEUED` + job `PENDING`, Redis is wake-up only
  - arq job id `{version_id}:{attempt}`; `enqueue_job() is None` is an error
  - Worker: `arq cited_rag.workers.ingestion_worker.WorkerSettings`
  - Transient retry: persist `PENDING`, `arq.Retry(defer=lease+1)`
  - `MemoryJobQueue` only when `environment=test` and Redis unset
  - `FAILED → QUEUED` retry resets job `PENDING` with a new attempt id

- **Decisions made in this phase (not already in ADR-011):**
  - Redis is not the source of truth for jobs; Postgres lease is.
  - Single `UPDATE … WHERE pending OR expired RUNNING RETURNING` for claim.
  - FastAPI UoW does not auto-commit; services `commit()` (from PR #7).
  - Phase 03 pipeline is a no-op that leaves the version `PROCESSING` (not `READY`).

- **Verification run (exact commands + results):**
  - PR #6 CI: `lint-type-unit` SUCCESS, `integration-postgres` SUCCESS
  - `main` push after merge: CI run `34109138167` SUCCESS
  - Local (pre-merge): ruff/mypy passed; `pytest tests/unit` **50 passed**; `pytest tests/integration` **29 passed** against local `cited_rag_test`

- **Not verified / known gaps:**
  - Live Docker `upload → Redis → worker → Postgres` not executed (Docker daemon did not respond to `docker info`)
  - Worker does not parse/chunk/index; `READY` is still forbidden
  - Phase status not `COMPLETE` until Compose path is observed or explicitly waived

- **Follow-ups for the next phase:**
  - Phase 04: Docling parser adapter, page provenance, persist pages (`implementation/phase-04-pdf-parsing-provenance.md`)
  - New branch from `origin/main` (`f91e47f` or later). Do not start Phase 04 on this docs branch.

### Phase 02 — PDF Upload, Object Storage, and Document Lifecycle

- **Date:** 2026-09-06
- **Branch:** `phase-02-upload-storage-lifecycle`
- **PR:** [#5](https://github.com/pranjulya/cited-RAG-Bot/pull/5) (`phase-02-upload-storage-lifecycle` → `main`; OPEN when written, now MERGED)
- **Status in phase file:** `TESTED`
- **Goal:** Accept PDF uploads into a collection, persist source files locally, create document/version metadata, API-key collection authorization. Not searchable.

- **Files added/changed:**
  - `src/cited_rag/api/deps.py`, `api/routes/collections.py`, `api/routes/documents.py`
  - `src/cited_rag/application/upload.py` — spool, hash, idempotency, compensation delete
  - `src/cited_rag/ports/object_storage.py`, `adapters/storage/local.py`
  - `src/cited_rag/domain/pdf.py` — extension, MIME, `%PDF` magic, size, empty
  - Settings: `local_storage_path`, `max_upload_bytes`
  - Tests: validation, local storage, auth 401, upload integration
  - `Learning/02-upload-storage-lifecycle.md`

- **Public contracts / commands:**
  - Header: `Authorization: Bearer <CITED_RAG_API_KEY>`
  - `POST /v1/collections` → `201`
  - `GET /v1/collections/{collection_id}` → `200` or `404`
  - `POST /v1/collections/{id}/documents` multipart `file` → `202` `{"document_id","document_version_id","status":"QUEUED"}`
  - Persist version `UPLOADED`; public status maps `UPLOADED` → `QUEUED`
  - Same hash in one collection is idempotent; same hash in two collections is allowed
  - `GET`/`DELETE /v1/documents/{id}` → `404` if missing or unauthorized
  - Object key: `collections/{collection_id}/documents/{document_id}/versions/{version_id}/source.pdf`
  - List-all-collections / list-documents-in-collection omitted
  - `/ready` still `not_configured`

- **Decisions made in this phase (not already in ADR-011):**
  - One V1 API principal (`uuid5` of a fixed name), not a stored key hash (Phase 18 can harden)
  - Non-READY versions are tombstoned to `DELETED` on document delete so the content-hash unique index can be reused; READY uses `READY → DELETING → DELETED`
  - `application/octet-stream` accepted if filename is `.pdf` and magic is `%PDF`

- **Verification run (exact commands + results):**
  - ruff / mypy — passed
  - `pytest tests/unit` — **45 passed**
  - `pytest tests/integration` — **20 passed** (local Homebrew Postgres)

- **Not verified / known gaps:**
  - Docker Compose API+Postgres not run (daemon not running)
  - S3 adapter not implemented (Phase later / production-style)
  - No ingestion worker (Phase 03)
  - Phase status `TESTED`, not `COMPLETE`

- **Follow-ups for the next phase:**
  - Review and merge [PR #5](https://github.com/pranjulya/cited-RAG-Bot/pull/5)
  - Phase 03: arq/Redis worker, `QUEUED → PROCESSING`, never `READY`
  - New branch from merged `main`

### Phase 01 — Core Domain Model and Persistence Foundation

- **Date:** 2026-09-06
- **Branch:** `phase-01-domain-persistence`
- **PR:** [#3](https://github.com/pranjulya/cited-RAG-Bot/pull/3) (`phase-01-domain-persistence` → `main`; OPEN when written, now MERGED)
- **Status in phase file:** `TESTED`
- **Goal:** Durable domain entities and PostgreSQL persistence for the collection → document → version → page → chunk chain. No upload, no retrieval API.

- **Files added/changed:**
  - `src/cited_rag/domain/` — enums, lifecycle policy, UUIDv5 chunk ids, frozen entities including `RetrievedCandidate`
  - `src/cited_rag/ports/repositories.py` — repository + unit-of-work ports
  - `src/cited_rag/adapters/persistence/postgres/` — SQLAlchemy mappings, repositories, `PostgresUnitOfWork`
  - `alembic.ini`, `alembic/env.py`, `alembic/versions/0001_core_metadata.py`
  - `pyproject.toml` — SQLAlchemy, asyncpg, Alembic, pytest-asyncio
  - `docker-compose.yml` — Postgres 16; API `CITED_RAG_DATABASE_URL`
  - `.github/workflows/ci.yml` — `integration-postgres` job
  - tests: lifecycle, chunk identity, retrieved candidate, DB unavailable, persistence round-trips
  - `Learning/01-domain-persistence.md`, README, phase status → `TESTED`

- **Public contracts / commands:**
  - Settings: optional `CITED_RAG_DATABASE_URL` (`SecretStr`; asyncpg URL)
  - `/ready` still `{"status":"not_configured"}`
  - Migrate: `alembic upgrade head` (requires `CITED_RAG_DATABASE_URL`)
  - Lifecycle: `UPLOADED → QUEUED → PROCESSING → READY|FAILED`; `FAILED → QUEUED`; `READY → DELETING → DELETED`
  - Unique `(collection_id, content_hash)` among versions with `ingestion_status <> 'DELETED'`
  - Chunk id = UUIDv5 from version, page range, order, content hash
  - Verify: `ruff check . && ruff format --check . && mypy src && pytest tests/unit` and `pytest tests/integration` with `CITED_RAG_DATABASE_URL`

- **Decisions made in this phase (not already in ADR-011):**
  - `DocumentVersion.collection_id` is denormalized so the hash unique index does not join `documents`.
  - ORM rows are separate from frozen domain dataclasses; mapping lives in `mapping.py`.
  - Evaluation tables are not created (Phase 19). `query_stage_events` is not created; `query_runs` is the audit row.
  - API-key hashes are not stored; `api_principals` is an identity for `Collection.owner_id` (auth is Phase 02).
  - App factory still does not open a DB connection on startup.

- **Verification run (exact commands + results):**
  - `.venv/bin/ruff check .` — passed
  - `.venv/bin/ruff format --check .` — passed
  - `.venv/bin/mypy src` — passed
  - `.venv/bin/pytest tests/unit` — **33 passed**
  - `CITED_RAG_DATABASE_URL=postgresql+asyncpg://…/cited_rag_test pytest tests/integration` — **11 passed** (includes Alembic downgrade+upgrade in session setup)
  - `git push -u origin phase-01-domain-persistence` — succeeded
  - PR #3 opened

- **Not verified / known gaps:**
  - Docker Compose Postgres/API image not run (Docker daemon not running)
  - GitHub Actions `integration-postgres` not observed green at handoff time
  - Phase status: `TESTED` when written; merged since; still not `COMPLETE`

- **Follow-ups for the next phase:**
  - Review and merge [PR #3](https://github.com/pranjulya/cited-RAG-Bot/pull/3). Do not start Phase 02 on this branch.
  - Phase 02: PDF upload, object storage, lifecycle, API-key collection auth (`implementation/phase-02-upload-storage-lifecycle.md`). New branch from merged `main`.
  - `/ready` stays `not_configured` until a later phase adds real checks.

### Phase 00 — Repository and Application Foundation

- **Date:** 2026-09-06
- **Branch:** `phase-00-foundation`
- **PR:** [#2](https://github.com/pranjulya/cited-RAG-Bot/pull/2) (`phase-00-foundation` → `main`; OPEN when written, now MERGED)
- **Status in phase file:** `TESTED`
- **Goal:** Minimal FastAPI/Python foundation for later phases. No RAG, no Postgres, no Qdrant, no Redis, no parsing.

- **Files added/changed:**
  - `AGENTS.md`, `CLAUDE.md`, `implementation/README.md` — branch-per-change git workflow
  - `pyproject.toml` — Python ≥3.12, FastAPI, pydantic-settings, uvicorn; optional `dev` extras: pytest, ruff, mypy, httpx
  - `.gitignore`, `.env.example`, `.dockerignore`
  - `src/cited_rag/__init__.py`, `config.py`, `main.py`, `py.typed`
  - `src/cited_rag/api/__init__.py`, `api/health.py`
  - `tests/conftest.py`, `tests/unit/test_app.py`, `test_config.py`, `test_health.py`, `tests/integration/test_startup.py`
  - `Dockerfile`, `docker-compose.yml` (API only)
  - `.github/workflows/ci.yml` — ruff, mypy, `pytest tests/unit`
  - `README.md`, `Learning/README.md`, `Learning/00-application-foundation.md`
  - `implementation/phase-00-foundation.md` status → `TESTED`

- **Public contracts / commands:**
  - Settings prefix: `CITED_RAG_`
  - Fields: `environment` (`development` \| `test` \| `production`), `api_key` (`SecretStr`), `log_level`, `debug`, `correlation_id_header` (default `X-Correlation-ID`)
  - Extra settings forbidden. Production requires a real API key (not empty, not `replace-me`) and forces `debug=false`.
  - Factory: `cited_rag.main.create_app()`; module app: `cited_rag.main:app`
  - `GET /health` → HTTP 200 `{"status":"ok"}`
  - `GET /ready` → HTTP 200 `{"status":"not_configured"}` (Phase 00 skeleton; later phases replace with real dependency checks)
  - Correlation header echoed on responses
  - Local: `python3.12 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]" && cp .env.example .env`
  - Run: `uvicorn cited_rag.main:app --reload --host 0.0.0.0 --port 8000`
  - Verify: `ruff check . && ruff format --check . && mypy src && pytest tests/unit && pytest tests/integration`
  - Docker: `docker compose up --build` (API only; daemon was not running when Phase 00 was tested)

- **Decisions made in this phase (not already in ADR-011):**
  - Ruff/mypy/pytest config lives in `pyproject.toml`. Ruff excludes `docs/`, `implementation/`, `Learning/` so architecture markdown is not reformatted.
  - Tests set `CITED_RAG_ENVIRONMENT=test` in `tests/conftest.py` so they do not need production secrets.
  - Correlation ID is a FastAPI HTTP middleware in `main.py`, not a separate middleware module (LLD path comes later).
  - Phase 00 `config.py` is at package root; LLD may later add `config/settings.py` without a second package root.

- **Verification run (exact commands + results):**
  - `.venv/bin/ruff check .` — passed
  - `.venv/bin/ruff format --check .` — passed
  - `.venv/bin/mypy src` — passed
  - `.venv/bin/pytest tests/unit tests/integration -v` — **10 passed**
  - `git push -u origin phase-00-foundation` — succeeded after `workflow` scope was granted
  - First push attempt failed: GitHub OAuth without `workflow` cannot create `.github/workflows/ci.yml`

- **Not verified / known gaps:**
  - Docker image build/start not run (Docker daemon not running)
  - Phase status: `TESTED` when written; merged since; still not `COMPLETE`
  - Phase 00: PR #2 was open when written; merged since
  - Starlette TestClient/httpx deprecation warnings appeared; ignored for this phase

- **Follow-ups for the next phase:**
  - Review and merge [PR #2](https://github.com/pranjulya/cited-RAG-Bot/pull/2). Do not start Phase 01 on this branch.
  - Phase 01: domain model + PostgreSQL persistence (`implementation/phase-01-domain-persistence.md`). New branch e.g. `phase-01-domain-persistence` from merged `main`.
  - Add Postgres to compose/CI only in the phase that needs it.
  - After Phase 00 merge, `/ready` stays `not_configured` until a later phase adds real checks.
  - After PR #2 is merged, `/clear` is safe; the next session starts Phase 01 from `main`.

---

## Earlier architecture work (pre-code, already on `main`)

Needed so a cleared session does not re-litigate design.

- Independent review found ADR index Accepted while bodies/HLD/LLD still disagreed (lifecycle, READY, Qdrant schema, auth, citations, fail-closed).
- Freeze: `docs/architecture/decisions/ADR-011-v1-locked-policies.md` (Accepted). Merged to `main` as `fd4c760`, then residual wording as PR #1 (`7d2de76` / merge `d8725fb`).
- Locked highlights: `src/cited_rag/`; lifecycle `UPLOADED → QUEUED → PROCESSING → READY|FAILED` plus `DELETING → DELETED`; upload `202` is `QUEUED`; Postgres pages/chunks **before** Qdrant; one Qdrant collection, named vectors `dense`+`sparse` on chunk UUID, created in Phase 06, sparse+READY finalize in Phase 07; fail-closed retriever/reranker errors; no V1 citation repair; model sees `E1` + text only; public citations omit `chunk_id`; API-key from Phase 02; Phase 18 hardens only; same-hash in one collection is idempotent; `FAILED` retry is `FAILED → QUEUED`.
- Do not re-open LLD §27 / ADR-011 items in a phase file.

---

## Session habit

After each phase PR is open and this file is updated and pushed: **clear the chat**. The next session reads `MEMORY.md` first. Do not rely on compact/summary.
