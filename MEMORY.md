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
| Last completed work | Phase 00 implemented and verified locally; **PR not opened yet** |
| Phase file status | `TESTED` (not `COMPLETE` — needs human review after merge) |
| Branch | `phase-00-foundation` (tracks `origin/phase-00-foundation`) |
| Commits on branch | `3ef8e71` docs: require a branch and PR for every change; `2d86621` feat: add Phase 00 FastAPI application foundation |
| PR | Not created. Open from https://github.com/pranjulya/cited-RAG-Bot/pull/new/phase-00-foundation |
| `main` | `d8725fb` — architecture freeze + residual wording. **Do not push or merge to `main` except via PR.** |
| Next action | 1) Open/merge the Phase 00 PR. 2) Start Phase 01 on a **new** branch from updated `main`. |
| Blockers | Docker daemon was not running, so the API image was not built. GitHub `workflow` scope was added later; CI file is on the branch. |

Do **not** start Phase 01 until Phase 00 is merged to `main`.

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

## Phase records

### Phase 00 — Repository and Application Foundation

- **Date:** 2026-09-06
- **Branch:** `phase-00-foundation`
- **PR:** not opened yet — https://github.com/pranjulya/cited-RAG-Bot/pull/new/phase-00-foundation
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
  - Phase status is `TESTED`, not `COMPLETE` (review + merge still required)
  - No Phase 00 GitHub PR yet
  - Starlette TestClient/httpx deprecation warnings appeared; ignored for this phase

- **Follow-ups for the next phase:**
  - Open the Phase 00 PR, review, merge to `main`. Do not start Phase 01 on this branch.
  - Phase 01: domain model + PostgreSQL persistence (`implementation/phase-01-domain-persistence.md`). New branch e.g. `phase-01-domain-persistence` from merged `main`.
  - Add Postgres to compose/CI only in the phase that needs it.
  - After Phase 00 merge, `/ready` stays `not_configured` until a later phase adds real checks.
  - After the Phase 00 PR is opened, update this file’s **Current state** and the PR field above, then `/clear` is safe.

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
