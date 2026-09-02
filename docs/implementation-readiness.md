# Step 10 — Phase 00 Implementation Readiness

**Project:** Cited RAG Bot  
**Status:** APPROVED FOR PHASE 00 (read ADR-011 before coding)  
**Scope:** Pre-coding readiness only

## Purpose

This document is the final gate between architecture planning and implementation. It confirms that Phase 00 can begin without inventing architecture, repository conventions, or hidden requirements during coding.

## Read Before Coding

Every implementation agent must read, in this order:

1. `Implementation.md`
2. `implementation/README.md`
3. `implementation/phase-00-foundation.md`
4. `docs/architecture/architecture-review.md`
5. `docs/architecture/HLD.md`
6. `docs/architecture/LLD.md`
7. `docs/architecture/decisions/ADR-011-v1-locked-policies.md` and other accepted ADRs
8. `AGENTS.md`
9. `CLAUDE.md` when using Claude Code

## Phase 00 Scope

Phase 00 creates only the application foundation required by later phases.

Allowed work:

- Python project metadata and dependency groups;
- FastAPI package skeleton;
- typed environment configuration;
- application factory/lifecycle structure;
- `/health` liveness endpoint;
- `/ready` readiness skeleton;
- pytest configuration and initial tests;
- linting, formatting, and static typing configuration;
- Docker development baseline;
- `.env.example` and `.gitignore`;
- agent guidance and developer commands;
- minimal Learning notes for concepts introduced in Phase 00.

Explicitly forbidden in Phase 00:

- PDF parsing;
- chunking;
- embeddings;
- Qdrant indexing;
- dense or sparse retrieval;
- RRF;
- reranking;
- LLM integration;
- citation generation/validation;
- PostgreSQL domain schema beyond what is strictly necessary for foundation bootstrapping;
- Redis worker implementation;
- speculative abstractions for future phases.

## Repository Conventions

Target package layout:

```text
src/cited_rag/
├── __init__.py
├── main.py
├── config.py
└── api/
    ├── __init__.py
    └── health.py

tests/
├── unit/
└── integration/
```

Future packages must follow the LLD instead of being invented opportunistically.

## Engineering Rules

1. Use Python typing for public interfaces and domain boundaries.
2. Configuration comes from environment/settings objects, never hardcoded secrets.
3. Provider SDKs remain behind adapters when introduced in later phases.
4. API routes remain thin; business logic belongs in services/domain modules.
5. Keep files focused and small enough to review independently.
6. Prefer explicit failure states over hidden fallback behavior.
7. Do not add infrastructure that is not required by the current phase.
8. Add tests before or with implementation changes.
9. Do not mark the phase complete until tests, lint, type checks, documentation, and review pass.
10. Architecture changes require an ADR update before code changes.

## Phase 00 Test Gate

At minimum Phase 00 must prove:

- package imports cleanly;
- application factory creates the FastAPI app;
- `/health` returns HTTP 200;
- `/ready` has deterministic documented behavior;
- invalid required configuration fails with a clear error;
- test configuration does not require production credentials;
- linting passes;
- static type checking passes;
- unit tests pass;
- Docker build/start instructions are reproducible.

## Security Gate

Even in Phase 00:

- no secrets in repository files;
- `.env` is ignored;
- `.env.example` contains placeholders only;
- errors must not dump secret values;
- debug behavior must not be enabled by default for production configuration.

## Observability Gate

Phase 00 should establish correlation/logging conventions only where needed for the foundation. Full tracing and metrics belong to later phases, but early code must not make them difficult to add.

## Learning Gate

Before Phase 00 is COMPLETE, the learner should be able to explain:

- FastAPI application factory/lifecycle;
- liveness vs readiness;
- environment-based configuration;
- why API routes should stay thin;
- why pytest layers are separated;
- what linting and static typing catch;
- why Docker development parity matters.

## Commit / Review Strategy

Prefer small reviewable commits, for example:

```text
chore: initialize python project tooling
feat: add fastapi application foundation
test: add health and configuration tests
chore: add docker development baseline
docs: document phase 00 developer workflow
```

Do not combine future RAG features into these commits.

## Entry Criteria

Phase 00 may start because:

- PRD exists;
- ADR directions are frozen;
- HLD exists;
- architecture diagrams exist;
- evaluation strategy exists;
- LLD exists;
- master Implementation plan exists;
- detailed phase plans exist;
- architecture review approved implementation preparation;
- coding rules and scope boundaries are explicit.

## Exit Criteria

Step 10 is complete when this readiness document and agent rules are present. Phase 00 remains `NOT_STARTED` until actual implementation work begins.

**Decision:** Phase 00 implementation is authorized.