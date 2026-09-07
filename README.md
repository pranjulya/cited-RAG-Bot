# Cited RAG Bot

PDF-only question answering with page-level citations. V1 architecture is frozen in `docs/architecture/decisions/ADR-011-v1-locked-policies.md`.

Phase 06 embeds chunks and upserts dense named vectors in Qdrant. Sparse slots exist on the same points but stay empty. The worker still does not mark `READY`.

## Requirements

- Python 3.12+
- PostgreSQL 16 (local install or Docker) for persistence tests and migrations
- Redis 7 for the arq worker (optional in tests; a memory queue is used when `CITED_RAG_REDIS_URL` is unset)
- PDF parser backend: `pypdf` by default (`CITED_RAG_PARSER_BACKEND`). Docling is `pip install 'cited-rag[parser]'` then `CITED_RAG_PARSER_BACKEND=docling`
- Qdrant for dense indexing (local install or Docker)
- Docker (optional, for API, Postgres, Redis, Qdrant, and worker)

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Do not commit `.env`. Placeholders in `.env.example` are not production secrets.

## Run

```bash
uvicorn cited_rag.main:app --reload --host 0.0.0.0 --port 8000
arq cited_rag.workers.ingestion_worker.WorkerSettings
```

- Liveness: `GET /health` → `{"status":"ok"}` (unauthenticated)
- Readiness: `GET /ready` → `{"status":"ok"}` when Postgres and local storage work; HTTP 503 otherwise (unauthenticated)
- Authenticated `/v1/*` routes use `Authorization: Bearer <api_key>`
- `POST /v1/collections` → `201`
- `POST /v1/collections/{collection_id}/documents` (multipart PDF) → `202` `{"status":"QUEUED"}`
- List-all-collections and list-documents-in-collection are omitted in V1 so far

## Database

Copy `.env.example` to `.env` and set `CITED_RAG_DATABASE_URL` (async SQLAlchemy URL, `postgresql+asyncpg://…`).

```bash
docker compose up -d postgres redis qdrant
# or use a local Postgres and create the database yourself
alembic upgrade head
```

## Test, lint, types

```bash
ruff check . && ruff format --check .
mypy src
pytest tests/unit
CITED_RAG_DATABASE_URL=postgresql+asyncpg://cited_rag:cited_rag@localhost:5432/cited_rag \
CITED_RAG_QDRANT_URL=http://localhost:6333 pytest tests/integration
```

Persistence tests skip unless `CITED_RAG_DATABASE_URL` is set. Compose runs `alembic upgrade head` before the API starts.

## Docker

```bash
docker compose up --build
```

Compose starts PostgreSQL, Redis, Qdrant, the API, and the ingestion worker. The worker parses, chunks, and dense-indexes, then leaves versions `PROCESSING`.

## Layout

Application code lives in `src/cited_rag/`. Implementation proceeds one phase at a time from `implementation/`. Never commit or merge directly to `main`; use a branch and a pull request (`AGENTS.md`).
