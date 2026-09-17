# Cited RAG Bot

PDF-only question answering with **page-level citations**. A collection holds many PDFs. Answers may only use evidence the application supplied as `E1..En`. Invented citations fail the request.

Architecture freeze: `docs/architecture/decisions/ADR-011-v1-locked-policies.md`.

## Demo flow

Start Docker Desktop, then `docker compose up --build -d --wait`. `/v1/*` requires `Authorization: Bearer replace-me` (compose / `.env.example`). `/health` and `/ready` are open.

```bash
export AUTH='Authorization: Bearer replace-me'
curl -sS http://localhost:8000/health
curl -sS http://localhost:8000/ready
curl -sS -X POST http://localhost:8000/v1/collections \
  -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"policies"}'
# POST /v1/collections/{id}/documents  (multipart PDF) → 202 QUEUED
# GET  /v1/documents/{id} until status READY
# POST /v1/collections/{id}/query  {"question":"How much leave?"}
```

1. `POST /v1/collections` with the Bearer header → `201`
2. `POST /v1/collections/{id}/documents` (PDF) → `202 QUEUED`
3. Worker parses, chunks, indexes dense **and** sparse on the same chunk UUID, then `READY`
4. `POST /v1/collections/{id}/query` `{"question":"..."}` → `ANSWERED` with citations `{document_id, document_version_id, document_name, page_start, page_end}` or `INSUFFICIENT_EVIDENCE`

## Pipeline

```text
PDF → pages/chunks (Postgres) → dense + sparse (Qdrant)
query → dense & sparse retrieve → RRF → rerank → context (E1..)
      → generate → citation validate → response
```

Hybrid fusion is in-process Reciprocal Rank Fusion. Production timeouts fail closed (`DENSE_RETRIEVAL_ERROR`, `SPARSE_RETRIEVAL_ERROR`, `RERANKER_ERROR`, `GENERATION_PROVIDER_ERROR`). Empty hit lists still fuse. Hash embeddings / overlap rerank / heuristic generator are local defaults; measured fixture scores are in `reports/v1-defaults.md`.

## Measured retrieval (golden-v1)

Two-case fixture: one answerable policy sentence, one unanswerable question. Reproduce with `python -m cited_rag.evaluation --matrix`.

| Config | Recall@5 | MRR | nDCG@5 | Citation validity | False-answer |
|---|---:|---:|---:|---:|---:|
| dense-only | 1.000 | 0.250 | 0.815 | 1.000 | 0.000 |
| sparse-only | 1.000 | 0.500 | 1.000 | 1.000 | 0.000 |
| hybrid | 1.000 | 0.500 | 1.000 | 1.000 | 0.000 |
| hybrid-rerank | 1.000 | 0.500 | 1.000 | 1.000 | 0.000 |

Dense-only finds the page but ranks it worse. Sparse/hybrid/hybrid+rerank tie here because the answer is a lexical hit. V1 still ships hybrid RRF plus rerank (`CITED_RAG_RRF_K=60`, `CITED_RAG_RERANK_TOP_N=10`) so paraphrase questions keep a dense path. Full table including no-answer precision/recall: `reports/v1-defaults.md`.

## Limitations

- PDF-only, API-key auth, one application Qdrant collection
- No V1 citation repair
- Heuristic generator is not an LLM; hash embeddings are not a hosted encoder
- Scanned/image-only PDFs fail with `PDF_UNSUPPORTED` (no OCR); paraphrase questions may abstain with the heuristic generator
- Golden set is two cases. Scores above are reproducible, not a hosted-model bake-off

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

Compose publishes Postgres on **host 5433** (container 5432) so a local Postgres on 5432 is not used by mistake. `.env.example` already uses `localhost:5433`.

```bash
docker compose up -d postgres redis qdrant
# or use a local Postgres and create the database yourself
alembic upgrade head
```

## Test, lint, types, evaluation

```bash
ruff check . && ruff format --check .
mypy src
pytest tests/unit
python -m cited_rag.evaluation
python -m cited_rag.evaluation --matrix
# Compose-published Postgres is localhost:5433. CI services use 5432.
CITED_RAG_DATABASE_URL=postgresql+asyncpg://cited_rag:cited_rag@localhost:5433/cited_rag \
CITED_RAG_QDRANT_URL=http://localhost:6333 pytest tests/integration
```

Persistence tests skip unless `CITED_RAG_DATABASE_URL` is set. Compose runs `alembic upgrade head` before the API starts. CI also builds the compose stack and probes `/health` and `/ready` (`.github/workflows/ci.yml` job `compose-smoke`).

## Docker

```bash
docker compose up --build -d --wait
curl -sf http://localhost:8000/health
curl -sf http://localhost:8000/ready
curl -sf http://localhost:8080/
docker compose down -v
```

Compose starts PostgreSQL, Redis, Qdrant, Alembic migrate, the API, the ingestion worker, and the glass-box console (`http://localhost:8080`). Paste `replace-me` in the key gate. The browser calls the API at `http://localhost:8000` (not the Docker hostname `api`).

## Layout

Application code lives in `src/cited_rag/`. Phases live in `implementation/`. Learning notes in `Learning/`. Operations in `docs/operations/`. Never commit or merge directly to `main`; use a branch and a pull request (`AGENTS.md`).

Interview notes: `Learning/interview-qa.md`.
