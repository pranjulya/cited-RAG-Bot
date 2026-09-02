# Phase 00 — Repository and Application Foundation

**Status:** NOT_STARTED

## Goal
Create the minimal production-oriented Python/FastAPI foundation required by every later phase without implementing RAG behavior yet.

## Prerequisites
- Steps 1–7 reviewed.
- Step 9 architecture review must approve starting code.

## Architecture References
- `Implementation.md`
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
- `docker-compose.yml`
- `AGENTS.md`
- `CLAUDE.md`

## Implementation Tasks
1. Define Python package and dependency groups.
2. Add typed settings loaded from environment.
3. Create FastAPI application factory.
4. Add `/health` liveness endpoint.
5. Add `/ready` readiness skeleton that can later check required dependencies.
6. Configure pytest, linting, formatting, and static typing.
7. Add Docker development baseline.
8. Add coding-agent rules referencing `Implementation.md` and current phase.

## Required Tests
- application imports successfully;
- health returns 200;
- invalid configuration fails clearly;
- test configuration does not require production secrets.

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