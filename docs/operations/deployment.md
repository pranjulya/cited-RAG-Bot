# Deployment

## Local stack

```bash
cp .env.example .env
docker compose up --build
```

Compose starts PostgreSQL, Redis, Qdrant, Alembic migrate, API (`:8000`), and the ingestion worker. Postgres is published on host **5433** so a local Postgres on 5432 is not selected. Authenticated `/v1/*` calls need `Authorization: Bearer replace-me`. Secrets stay in `.env`, not in the image.

## Readiness

- `GET /health` — process is up
- `GET /ready` — Postgres and local storage accept connections

Liveness is “the process exists.” Readiness is “dependencies we need to serve traffic are up.” Migrations run as a one-shot `migrate` service before API/worker start.

## Production substitutions

| Compose | Production |
|---|---|
| postgres service | managed PostgreSQL 16 |
| redis service | managed Redis 7 |
| qdrant service | managed Qdrant or equivalent |
| `./data/objects` | S3-compatible bucket behind the storage port |
| hash embedder / overlap reranker / heuristic generator | hosted adapters, same ports |

Validate `CITED_RAG_ENVIRONMENT=production` has a real API key, database URL, Redis URL, and Qdrant URL. Do not bake those values into the image.
