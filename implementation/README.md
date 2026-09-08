# Project 04 — Phase Implementation Guide

**Status:** PLANNING COMPLETE, ADR-011 FROZEN, PHASE 10 IN_PROGRESS

This folder is the execution layer for `Implementation.md`. Each phase is intentionally small enough to implement, test, review, learn, and complete before moving to the next dependency.

## Execution Rule

Before any phase:

1. Read `MEMORY.md` (Current state). Do not start the next phase if the previous PR is still unmerged unless Current state says otherwise.
2. Read `Implementation.md`.
3. Read the phase file.
4. Read referenced PRD/HLD/LLD/ADR/evaluation docs.
5. Verify prerequisites.
6. Create a branch from latest `main` (never commit to `main`; see `AGENTS.md` Git Workflow).
7. Write or identify failing tests first.
8. Implement only the current phase.
9. Run the phase verification suite.
10. Update Learning documentation.
11. Review architecture/security implications.
12. Change phase status only when its Definition of Done is satisfied.
13. Open a pull request into `main`.
14. Update `MEMORY.md` (Current state + phase record) and push on the phase branch. Then the chat may be cleared.

## Status Model

`NOT_STARTED → IN_PROGRESS → IMPLEMENTED → TESTED → REVIEWED → COMPLETE`

## Phase Index

| Phase | Name | Depends On |
|---|---|---|
| 00 | Repository and Application Foundation | Architecture review gate |
| 01 | Core Domain Model and Persistence | 00 |
| 02 | PDF Upload, Object Storage, Lifecycle | 01 |
| 03 | Asynchronous Ingestion Worker | 02 |
| 04 | PDF Parsing and Page Provenance | 03 |
| 05 | Provenance-Aware Chunking | 04 |
| 06 | Embedding and Dense Indexing | 05 |
| 07 | Sparse Indexing, Retrieval, READY finalize | 06 (Qdrant named-vector collection must exist) |
| 08 | Dense Retrieval | 06 |
| 09 | Hybrid Retrieval and RRF | 07, 08 |
| 10 | Reranking | 09 |
| 11 | Context Builder and Evidence Contract | 10 |
| 12 | Grounded Generation | 11 |
| 13 | Citation Mapping and Validation | 12 |
| 14 | No-Answer Decision Policy | 11–13 |
| 15 | End-to-End Query API | 14 |
| 16 | Document Deletion and Index Consistency | 02, 03, 06, 07 (query-race tests after 15) |
| 17 | Observability | 03, 15 |
| 18 | Security Hardening | 15–17 |
| 19 | Evaluation Harness | 09–15 |
| 20 | RAG Quality Experiments | 19 |
| 21 | Production Failure Scenarios | 15–20 |
| 22 | Docker, CI, Deployment Readiness | 00–21 |
| 23 | Documentation, Learning, Interview Readiness | all prior phases |

## Cross-Cutting Invariants

- PDF-only V1.
- Multi-PDF collections.
- Retrieval always scoped by collection.
- Provenance survives page → chunk → retrieval → rerank → evidence ID → citation.
- PostgreSQL is authoritative metadata/provenance state.
- Retrieval indexes are derived artifacts.
- Provider SDKs stay behind adapters.
- Retrieved PDF content is untrusted data.
- The LLM never invents authoritative document/page/chunk identifiers and never receives those identifiers in the prompt.
- Production retrieval is fail-closed on dependency failure; empty hit lists still fuse.
- Only the active READY document version is searchable.
- Read `docs/architecture/decisions/ADR-011-v1-locked-policies.md` with every phase.
- No-answer is a valid success outcome.
- Evaluation measures retrieval, reranking, grounding, citation quality, and no-answer separately.

## TDD and Commit Discipline

Each phase should be executed in reviewer-sized tasks. For deterministic behavior, use the cycle: failing test → minimal implementation → passing test → refactor → full phase tests → commit. External-provider code should use adapter contract tests and deterministic fakes for unit tests.

## Learning Rule

A phase is not COMPLETE until the engineer can explain the concepts listed in its `What I Must Be Able to Explain` section without relying on generated code.