# Cited RAG Bot

PDF-only question answering with page-level citations. V1 architecture is frozen in `docs/architecture/decisions/ADR-011-v1-locked-policies.md`.

Phase 00 is the application foundation only: FastAPI, configuration, health/readiness, tests, lint, types, and an API-only Docker image. There is no RAG behavior yet.

## Requirements

- Python 3.12+
- Docker (optional, for the API image)

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

## Test, lint, types

```bash
ruff check . && ruff format --check .
mypy src
pytest tests/unit
pytest tests/integration
```

## Docker (API only)

```bash
docker compose up --build
```

PostgreSQL, Redis, and Qdrant are not part of this phase.

## Layout

Application code lives in `src/cited_rag/`. Implementation proceeds one phase at a time from `implementation/`. Never commit or merge directly to `main`; use a branch and a pull request (`AGENTS.md`).
