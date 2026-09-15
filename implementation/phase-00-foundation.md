# Phase 00 — Repository and Application Foundation

**Status:** REVIEWED
**On main:** merged PR #2. **Not COMPLETE:** AGENTS.md COMPLETE requires a recorded Definition of Done (implementation, tests, review, docs, Learning) at close-out; that was not recorded.

## Goal
Create the minimal production-oriented Python/FastAPI foundation required by every later phase without implementing RAG behavior yet.

## Prerequisites
- Steps 1–7 reviewed.
- Step 9 architecture review passed.
- Step 10 implementation readiness present.
- ADR-011 V1 locks accepted.

## Architecture References
- `Implementation.md`
- `docs/architecture/decisions/ADR-011-v1-locked-policies.md`
- `docs/architecture/HLD.md`
- `docs/architecture/LLD.md`

## Concepts to Learn
FastAPI application lifecycle, dependency injection, Pydantic settings, package boundaries, health vs readiness, pytest structure, linting, typing, Docker development.

## Planned Deliverables
- `pyproject.toml`
- `.env.example`
- `.gitignore`
- `src/cited_rag/main.py`
- `src/cited_rag/config.py`
- `src/cited_rag/api/health.py`
- `tests/unit/`
- `tests/integration/`
- `Dockerfile`
- `docker-compose.yml` (API only in this phase)
- root `README.md` with install/test/run commands
- `Learning/README.md`
- `.github/workflows/ci.yml` (ruff, mypy, unit tests)
- do **not** recreate existing `AGENTS.md` / `CLAUDE.md`

## Implementation Tasks
1. Define Python package `src/cited_rag` and dependency groups.
2. Add typed settings loaded from environment (`CITED_RAG_` prefix), including a placeholder API-key setting. Do not hardcode later RAG knobs as literals in adapters; add settings fields as phases need them.
3. Create FastAPI application factory.
4. Add `/health` liveness endpoint.
5. Add `/ready` skeleton that returns a documented body such as `{"status":"not_configured"}` until dependency checks exist. Deterministic: HTTP 200 with that contract in Phase 00.
6. Configure pytest, linting, formatting, and static typing.
7. Add Docker development baseline for the API image only.
8. Add root README, `Learning/` stub, and CI for lint/type/unit. Keep existing agent rule files.

## Security
No secrets in the repo. `.env` gitignored. `.env.example` placeholders only. Debug disabled when `environment=production`. Do not log API keys.

## Observability
Correlation-id / structured logging conventions only. No metrics stack yet.

## Required Tests
- application imports successfully;
- health returns 200;
- `/ready` returns the documented Phase 00 body;
- invalid configuration fails clearly;
- test configuration does not require production secrets;
- ruff and mypy pass in CI config.

## Failure Scenarios
Missing environment values, malformed config, application startup failure, Docker startup mismatch.

## Acceptance Criteria
- application starts locally;
- health endpoint passes;
- lint/type/test commands are documented and pass;
- no RAG-specific logic exists yet.

## Definition of Done
Implementation, tests, review, documentation, and Learning notes are complete.

## What I Must Be Able to Explain
Why use an application factory? Difference between liveness and readiness? Why centralize configuration? Why keep RAG logic out of the API layer?