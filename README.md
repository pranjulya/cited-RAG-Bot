# Cited RAG Bot

PDF-only question answering with **page-level citations**. A collection holds many PDFs. Answers may only use evidence the application supplied as `E1..En`. Invented citations fail the request.

Architecture freeze: `docs/architecture/decisions/ADR-011-v1-locked-policies.md`.

## Demo flow

1. `POST /v1/collections`
2. `POST /v1/collections/{id}/documents` (PDF) → `202 QUEUED`
3. Worker parses, chunks, indexes dense **and** sparse on the same chunk UUID, then `READY`
4. `POST /v1/collections/{id}/query` `{"question":"..."}` → `ANSWERED` with citations `{document_id, document_version_id, document_name, page_start, page_end}` or `INSUFFICIENT_EVIDENCE`

## Pipeline

```text
PDF → pages/chunks (Postgres) → dense + sparse (Qdrant)
query → dense & sparse retrieve → RRF → rerank → context (E1..)
      → generate → citation validate → response
```

Hybrid fusion is in-process Reciprocal Rank Fusion. Production timeouts fail closed (`DENSE_RETRIEVAL_ERROR`, `SPARSE_RETRIEVAL_ERROR`, `RERANKER_ERROR`, `GENERATION_PROVIDER_ERROR`). Empty hit lists still fuse. Hash embeddings / overlap rerank / heuristic generator are local defaults, not quality claims (`reports/v1-defaults.md`).

## Limitations

- PDF-only, API-key auth, one application Qdrant collection
- No V1 citation repair
- Heuristic generator is not an LLM
- Evaluation golden set is a tiny fixture until a hosted model is measured

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
- `POST /v1/collections/{collection_id}/query` → `200` `ANSWERED` | `INSUFFICIENT_EVIDENCE`
- `DELETE /v1/documents/{document_id}` → `202` `DELETING` (tombstone, then index purge)
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

Compose starts PostgreSQL, Redis, Qdrant, the API, and the ingestion worker. The worker parses, chunks, dense-indexes, sparse-indexes, then marks versions `READY`.

## Layout

Application code lives in `src/cited_rag/`. Phases live in `implementation/`. Learning notes in `Learning/`. Operations in `docs/operations/`. Never commit or merge directly to `main`; use a branch and a pull request (`AGENTS.md`).

Interview notes: `Learning/interview-qa.md`.
