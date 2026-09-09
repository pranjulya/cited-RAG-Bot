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
| Last completed work | Phase 08 **[#13](https://github.com/pranjulya/cited-RAG-Bot/pull/13)** merged (`b6d7774`). Phase 09 hybrid RRF opened. |
| Phase file status | Phase 09 `IN_PROGRESS` (not `TESTED`) |
| Branch | `phase-09-hybrid-rrf` |
| PR | [#14](https://github.com/pranjulya/cited-RAG-Bot/pull/14) — open |
| `main` | `b6d7774` — Phase 08 dense retrieval. **Do not push or merge to `main` except via PR.** |
| Next action | Codex review of Phase 09. Phase 10 reranking is stacked after this PR is opened; merge #14 before #15. |
| Blockers | Local Docker/Qdrant hybrid integration not run. |

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

### Phase 09 — Hybrid Retrieval and RRF

- **Date:** 2026-09-09
- **Branch:** `phase-09-hybrid-rrf`
- **PR:** [#14](https://github.com/pranjulya/cited-RAG-Bot/pull/14) (`phase-09-hybrid-rrf` → `main`, OPEN)
- **Status in phase file:** `IN_PROGRESS`
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
- **Status in phase file:** `IN_PROGRESS` (merged)
- **Goal:** Collection-scoped dense retrieval over READY version ids with fail-closed payload validation.

- **Follow-ups for the next phase:**
  - Phase 09 hybrid RRF (opened as #14)

### Phase 07 — Sparse Indexing and Retrieval

- **Date:** 2026-09-08
- **Branch:** `phase-07-sparse-indexing-retrieval`
- **PR:** [#12](https://github.com/pranjulya/cited-RAG-Bot/pull/12) (`phase-07-sparse-indexing-retrieval` → `main`, MERGED `b9ec137`)
- **Status in phase file:** `IN_PROGRESS`
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
- **Status in phase file:** `IN_PROGRESS` (merged; CI integration passed)
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
- **Status in phase file:** `REVIEWED` (was `TESTED` at merge; not `COMPLETE`)
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
- **PR:** [#5](https://github.com/pranjulya/cited-RAG-Bot/pull/5) (`phase-02-upload-storage-lifecycle` → `main`, OPEN)
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
- **PR:** [#3](https://github.com/pranjulya/cited-RAG-Bot/pull/3) (`phase-01-domain-persistence` → `main`, OPEN)
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
  - Phase status is `TESTED`, not `COMPLETE` (review + merge still required)

- **Follow-ups for the next phase:**
  - Review and merge [PR #3](https://github.com/pranjulya/cited-RAG-Bot/pull/3). Do not start Phase 02 on this branch.
  - Phase 02: PDF upload, object storage, lifecycle, API-key collection auth (`implementation/phase-02-upload-storage-lifecycle.md`). New branch from merged `main`.
  - `/ready` stays `not_configured` until a later phase adds real checks.

### Phase 00 — Repository and Application Foundation

- **Date:** 2026-09-06
- **Branch:** `phase-00-foundation`
- **PR:** [#2](https://github.com/pranjulya/cited-RAG-Bot/pull/2) (`phase-00-foundation` → `main`, OPEN)
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
  - Phase 00 PR is open (#2); not merged yet
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
