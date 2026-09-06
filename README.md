# Cited RAG Bot

PDF-only question answering with page-level citations. V1 architecture is frozen in `docs/architecture/decisions/ADR-011-v1-locked-policies.md`.

Phase 01 adds the durable domain model and PostgreSQL persistence. There is still no upload or retrieval API.

## Requirements

- Python 3.12+
- PostgreSQL 16 (local install or Docker) for persistence tests and migrations
- Docker (optional, for the API image plus Postgres)

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
```

- Liveness: `GET /health` → `{"status":"ok"}`
- Phase 00 readiness: `GET /ready` → `{"status":"not_configured"}` (HTTP 200)

## Database

Copy `.env.example` to `.env` and set `CITED_RAG_DATABASE_URL` (async SQLAlchemy URL, `postgresql+asyncpg://…`).

```bash
docker compose up -d postgres
# or use a local Postgres and create the database yourself
alembic upgrade head
```

## Test, lint, types

```bash
ruff check . && ruff format --check .
mypy src
pytest tests/unit
CITED_RAG_DATABASE_URL=postgresql+asyncpg://cited_rag:cited_rag@localhost:5432/cited_rag pytest tests/integration
```

Persistence tests skip unless `CITED_RAG_DATABASE_URL` is set. `/ready` remains `{"status":"not_configured"}` in this phase.

## Docker

```bash
docker compose up --build
```

Compose now starts PostgreSQL and the API. Redis and Qdrant are still out of scope.

## Layout

Application code lives in `src/cited_rag/`. Implementation proceeds one phase at a time from `implementation/`. Never commit or merge directly to `main`; use a branch and a pull request (`AGENTS.md`).
