# Phase 00 — Application Foundation

## Why an application factory?

`create_app()` builds a FastAPI instance from settings. Tests can pass explicit settings. Docker and uvicorn import `cited_rag.main:app`. Startup side effects stay in one place instead of happening at import in every module.

## Liveness vs readiness

`/health` answers: is this process running? It must not fail because Postgres or Qdrant is down.

`/ready` answers: can this process take work? In Phase 00 there are no dependencies yet, so the contract is HTTP 200 with `{"status":"not_configured"}`. Later phases replace that body with real dependency checks. Do not invent a 503 here until those checks exist.

## Why centralize configuration?

All settings load from `CITED_RAG_` environment variables through `cited_rag.config.Settings`. Adapters must not hardcode model names, keys, or hostnames. Production forces `debug=false` and rejects a missing or placeholder API key. Secrets use `SecretStr` so they do not appear in `repr`.

## Why keep RAG out of the API layer?

Routes stay thin. Health handlers return a dict. Retrieval, ingestion, and citations will live in application/domain modules. Putting RAG in `api/` would mix HTTP with business rules and make tests depend on FastAPI.

## Pytest layers

`tests/unit` covers configuration and HTTP contracts without Docker. `tests/integration` covers process startup through the factory. Later phases add adapter/integration tests that need Postgres, Redis, or Qdrant.

## Lint and types

Ruff catches unused imports, style, and a class of bugs. Mypy catches type mistakes at the package boundary. CI runs both plus unit tests on every push and pull request.

## Docker parity

The Phase 00 image runs the same FastAPI app as local uvicorn. Compose starts only the API. Databases join in the phases that introduce them so we do not run unused infrastructure.
