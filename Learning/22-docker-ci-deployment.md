# Phase 22 — Docker, CI, and Deployment

## Liveness vs readiness

`/health` means the API process started. `/ready` means Postgres and storage work. A container can be alive and still unready while migrations run.

## Why migrations are a deploy step

Schema changes are not idempotent with live writes. Compose runs `alembic upgrade head` to completion before API/worker. Production should do the same in the release pipeline, not lazily on first request.

## Image vs secret store

The image contains code and default non-secret config. API keys, database URLs, and cloud credentials come from the environment or a secret manager. `.env` is local-only and gitignored.
