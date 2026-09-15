# AGENTS.md

## Purpose

This file defines repository-wide rules for Codex and other coding agents working on Cited RAG Bot.

## Mandatory Reading Order

Before changing code:

1. `MEMORY.md` (cold-start handoff; **Current state** first)
2. `Implementation.md`
3. `docs/architecture/decisions/ADR-011-v1-locked-policies.md`
4. `docs/architecture/decisions/ADR-012-glass-box-console.md` when the work is UI
5. `implementation/README.md` and, for UI, `implementation/ui/README.md`
6. the current `implementation/phase-XX-*.md` or `implementation/ui/ui-XX-*.md`
7. `docs/architecture/architecture-review.md`
8. relevant PRD/HLD/LLD/ADR/evaluation documents

## Execution Rules

1. Work on one implementation phase at a time.
2. Confirm prerequisites before starting a phase.
3. State expected files and tests before implementation.
4. Do not implement future phases opportunistically.
5. Do not silently change architecture.
6. Architecture changes require ADR review/update first.
7. Use tests to drive deterministic behavior where practical.
8. Keep provider SDKs behind adapters.
9. Keep API routes thin.
10. Preserve collection/document/version/page/chunk provenance wherever the current phase touches evidence.
11. Never invent or weaken collection scoping.
12. Never log secrets or sensitive document content by default.
13. Do not add unnecessary infrastructure or abstractions.
14. Update the current phase status only when its stated gate is actually satisfied.
15. Update Learning documentation for concepts introduced by the phase.
16. After a phase is verified and its pull request is opened, update `MEMORY.md` (Current state + a full phase record) and push it on the phase branch **before** the chat is cleared. Do not dump transcripts or secrets. The next session must read `MEMORY.md` first and must not start the next phase until Current state says the previous PR is merged, unless Current state records an explicit exception.

## Git Workflow

Never commit, push, or merge directly to `main`.

1. Create a new branch from the latest `main` for every implementation phase, feature, and bug fix.
2. Do not combine unrelated phases or bug fixes on the same branch.
3. Open a pull request into `main`. Merge only after review. Do not fast-forward or push commits onto `main` from an agent session unless the user explicitly asks to merge a reviewed PR.
4. Suggested names: `phase-00-foundation`, `phase-01-domain-persistence`, `fix/<short-name>`.

## Phase Status

Allowed phase statuses:

```text
NOT_STARTED
IN_PROGRESS
IMPLEMENTED
TESTED
REVIEWED
COMPLETE
```

`COMPLETE` means implementation, automated tests, review, documentation, and learning notes all satisfy the phase Definition of Done.

## Testing Expectations

Use the test level appropriate to the change:

- unit tests for deterministic logic;
- contract tests for adapters;
- integration tests for databases, queues, storage, retrieval systems, and provider boundaries;
- end-to-end tests for complete user flows;
- evaluation tests for RAG quality.

Do not substitute mocked tests for integration behavior that the current phase explicitly requires.

## Architecture Invariants

- V1 is PDF-only.
- Queries are collection-scoped.
- PostgreSQL is authoritative durable metadata/provenance state.
- Retrieval indexes are derived state.
- Ingestion is asynchronous.
- Dense and sparse retrieval are both mandatory for READY documents.
- Hybrid retrieval uses explicit fusion.
- Generation may use only approved evidence.
- Citation identities are application-owned.
- Citations must be validated before returning them.
- Retrieved PDF text is untrusted data.
- Unsupported questions must support controlled insufficient-evidence behavior.

## Completion Rule

Before claiming a phase complete, run and report the exact verification required by that phase. Evidence before completion claims.