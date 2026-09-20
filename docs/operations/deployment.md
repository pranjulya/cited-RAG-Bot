# Deployment

## Local stack

```bash
cp .env.example .env
docker compose up --build
```

Compose starts PostgreSQL, Redis, Qdrant, Alembic migrate, API (`:8000`), ingestion worker, and the console (`:8080`). Postgres is published on host **5433** so a local Postgres on 5432 is not selected. Authenticated `/v1/*` calls need `Authorization: Bearer replace-me`. Secrets stay in `.env`, not in the image.

## Hosted generation demo

CI and local defaults use the deterministic heuristic generator. To point the
API at an OpenAI-compatible provider, set these server-side values in `.env`
(never `VITE_*`, and never in the browser):

```bash
CITED_RAG_GENERATION_BACKEND=openai_compatible
CITED_RAG_GENERATION_BASE_URL=https://api.openai.com/v1
CITED_RAG_GENERATION_MODEL=gpt-4o-mini
CITED_RAG_GENERATION_API_KEY=replace-with-a-server-secret
```

The same shape works with compatible providers such as xAI by changing the
base URL and model. A missing hosted key fails startup; the API never silently
falls back to heuristic generation.

## Readiness

- `GET /health` — process is up
- `GET /ready` — Postgres and local storage accept connections

Liveness is “the process exists.” Readiness is “dependencies we need to serve traffic are up.” Migrations run as a one-shot `migrate` service before API/worker start.

## Console origin and CORS

The static console is served by nginx on `http://localhost:8080` and calls the
API origin at `http://localhost:8000`. For a deployed console, build the web
image with the public API origin (`VITE_API_BASE_URL`) and set the API's
`CITED_RAG_CORS_ALLOW_ORIGINS` to the exact console origin, for example:

```bash
CITED_RAG_CORS_ALLOW_ORIGINS=https://console.example.com
```

Production rejects the wildcard CORS value. The browser key remains in
tab-scoped `sessionStorage`; it is not a build argument, image layer, or
`VITE_*` variable.

## Production substitutions

| Compose | Production |
|---|---|
| postgres service | managed PostgreSQL 16 |
| redis service | managed Redis 7 |
| qdrant service | managed Qdrant or equivalent |
| `./data/objects` | S3-compatible bucket behind the storage port |
| hash embedder / overlap reranker / heuristic generator | hosted adapters, same ports |

Validate `CITED_RAG_ENVIRONMENT=production` has a real API key, database URL, Redis URL, and Qdrant URL. Do not bake those values into the image.
