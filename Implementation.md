# Project 04 — Cited RAG Bot

## Master Implementation Plan

**Status:** Accepted for implementation (ADR-011 freeze); Phase 03 merged (`REVIEWED`); next is Phase 04  
**Version:** 1.1  
**Scope:** PDF-only, multi-document Cited RAG with page-level citations

---

## 1. Purpose

This document is the master execution roadmap for Project 04 — Cited RAG Bot.

It does not replace the detailed product and architecture documents. Instead, it defines how those approved designs are converted into an ordered, reviewable, testable implementation.

The coding agent must treat this file as the implementation source of truth and follow the linked design documents before changing architecture or writing code.

---

## 2. Authoritative Design Documents

Before implementing any phase, read the relevant documents below.

### Product

- `docs/product/PRD.md`

### Architecture Decisions

- `docs/architecture/decisions/README.md`
- `docs/architecture/decisions/ADR-001-pdf-parser.md`
- `docs/architecture/decisions/ADR-002-metadata-persistence.md`
- `docs/architecture/decisions/ADR-003-retrieval-store.md`
- `docs/architecture/decisions/ADR-004-hybrid-retrieval.md`
- `docs/architecture/decisions/ADR-005-reranking.md`
- `docs/architecture/decisions/ADR-006-citation-contract.md`
- `docs/architecture/decisions/ADR-007-async-ingestion.md`
- `docs/architecture/decisions/ADR-008-source-pdf-storage.md`
- `docs/architecture/decisions/ADR-009-provider-boundaries.md`
- `docs/architecture/decisions/ADR-010-evaluation-gates.md`
- `docs/architecture/decisions/ADR-011-v1-locked-policies.md`

### Architecture

- `docs/architecture/HLD.md`
- `docs/architecture/LLD.md`

### Architecture Diagrams

- `docs/architecture/diagrams/README.md`
- `docs/architecture/diagrams/01-system-context.md`
- `docs/architecture/diagrams/02-ingestion-flow.md`
- `docs/architecture/diagrams/03-query-retrieval-flow.md`
- `docs/architecture/diagrams/04-sequence-diagrams.md`
- `docs/architecture/diagrams/05-deployment-runtime.md`
- `docs/architecture/diagrams/06-data-provenance.md`

### Evaluation

- `docs/evaluation/evaluation-strategy.md`

---

## 3. Product Contract That Must Not Be Broken

V1 is intentionally constrained.

The implementation must preserve these rules:

1. PDF-only ingestion.
2. Multiple PDFs may belong to one collection.
3. Retrieval is always collection-scoped.
4. Page provenance must survive parsing, chunking, indexing, retrieval, reranking, context construction, and citation generation.
5. Dense and sparse retrieval must both be supported.
6. Hybrid retrieval must use an explicit fusion strategy.
7. Retrieved candidates must be reranked before final context construction.
8. Generation must use only approved evidence.
9. The application owns citation identities. The model sees evidence IDs and text only.
10. The model may cite only request-scoped evidence IDs supplied by the application.
11. Returned citations must be deterministically validated. Fabricated IDs fail the request. Public citations omit `chunk_id`.
12. Unsupported questions must return a controlled insufficient-evidence result.
13. Evaluation must measure retrieval, reranking, answer grounding, citations, and no-answer behavior independently.
14. Source PDF content is untrusted data and must never become trusted system instruction.
15. Provider-specific SDK code must remain behind adapters/interfaces.

---

## 4. Accepted Technology Direction

The current architecture uses:

```text
API                  FastAPI / Python
Metadata             PostgreSQL
Retrieval             Qdrant
Queue / coordination Redis + arq worker
PDF parser            Docling behind parser abstraction
Hybrid fusion         Reciprocal Rank Fusion
Reranking             Replaceable cross-encoder / hosted adapter
PDF storage           Local adapter in development, S3-compatible in production
Observability         Structured logs + metrics + traces
Evaluation            Versioned golden dataset + automated evaluation harness
```

These are accepted. ADR-011 freezes lifecycle, Qdrant schema, auth, citations, fail-closed retrieval, and READY ownership. If an ADR changes, update this document before implementation continues.

---

## 5. High-Level Runtime Flow

### Ingestion

```text
Upload PDF
   ↓
Validate request/file
   ↓
Persist original PDF
   ↓
Create document/version metadata
   ↓
Enqueue ingestion job
   ↓
Parse PDF by page
   ↓
Normalize content
   ↓
Chunk with provenance
   ↓
Persist durable page/chunk metadata
   ↓
Generate dense + sparse representations
   ↓
Index retrieval artifacts (named vectors on chunk UUID)
   ↓
Verify dense + sparse completeness
   ↓
Mark document READY
```

### Query

```text
Question + collection_id
   ↓
Authorize collection
   ↓
Dense retrieval ───────┐
                        ├── RRF fusion
Sparse retrieval ──────┘
                            ↓
                         Reranker
                            ↓
                     Context Builder
                            ↓
                  Evidence IDs E1..En
                            ↓
                    Grounded Generation
                            ↓
                    Citation Validation
                            ↓
            Answer + Document/Page Citations
```

---

## 6. Implementation Strategy

The project will be implemented phase by phase.

Every phase has a dedicated file under `implementation/`.

Each phase file must contain:

- status;
- goal;
- why the phase exists;
- prerequisites;
- architecture references;
- concepts to learn;
- files to create/modify;
- implementation tasks;
- failure scenarios;
- tests;
- observability requirements where relevant;
- security requirements where relevant;
- acceptance criteria;
- Definition of Done;
- interview/learning questions.

A phase may not be marked complete because code merely exists.

---

## 7. Phase Status Model

Every implementation phase uses one of these statuses:

```text
NOT_STARTED
IN_PROGRESS
IMPLEMENTED
TESTED
REVIEWED
COMPLETE
```

Meaning:

- `NOT_STARTED` — no implementation work has begun.
- `IN_PROGRESS` — active implementation.
- `IMPLEMENTED` — intended code exists, but verification is incomplete.
- `TESTED` — required automated tests pass.
- `REVIEWED` — architecture/code review completed.
- `COMPLETE` — implementation, tests, review, documentation, and learning material satisfy phase DoD.

---

## 8. Planned Implementation Phases

### Phase 00 — Repository and Application Foundation

Establish Python/FastAPI structure, configuration, dependency management, test framework, lint/type tooling, environment conventions, health/readiness skeleton, Docker development baseline, and agent documentation.

### Phase 01 — Core Domain Model and Persistence Foundation

Implement collection, document, document-version, page, chunk, ingestion-job, and query/audit domain models plus PostgreSQL repository abstractions and migrations.

### Phase 02 — PDF Upload, Object Storage, and Document Lifecycle

Implement collection-scoped PDF upload, API-key collection authorization, file validation envelope, source storage abstraction, document/version creation, per-collection content-hash idempotency, lifecycle states including `QUEUED`, and status API.

### Phase 03 — Asynchronous Ingestion Worker

Introduce arq/Redis worker execution, idempotent job processing keyed by `document_version_id`, retries, `QUEUED → PROCESSING` (never `READY`), correlation IDs, and classified ingestion failures.

### Phase 04 — PDF Parsing and Page Provenance

Integrate the parser adapter, extract page-aware content, preserve PDF page numbers, handle corrupt/password-protected/extraction-empty PDFs, and persist page metadata.

### Phase 05 — Provenance-Aware Chunking

Implement configurable chunking while retaining document/version/page/chunk identity and deterministic chunk ordering.

### Phase 06 — Embedding and Dense Indexing

Implement embedding provider abstraction, batch embedding generation, and Qdrant collection creation with named vectors `dense` and `sparse`. Upsert dense vectors on chunk UUIDs with collection/version payload. Do not mark `READY`. Do not create a dense-only collection.

### Phase 07 — Sparse Indexing and Retrieval

Implement `SparseEncoder` (default FastEmbed BM42), sparse upserts on the **same** Qdrant points, collection-scoped sparse retrieval, shared `RetrievedCandidate`, and the ingestion-finalize check that sets `READY` only after dense + sparse artifacts exist.

### Phase 08 — Dense Retrieval

Implement collection-scoped semantic retrieval, configurable top-K behavior, candidate models, metadata filtering, telemetry, and retrieval tests.

### Phase 09 — Hybrid Retrieval and RRF

Run dense and sparse retrieval, deduplicate chunk candidates, apply in-process Reciprocal Rank Fusion, handle one-side-empty results, and fail closed on operational retriever failure.

### Phase 10 — Reranking

Implement replaceable reranker abstraction, candidate reranking, timeout → `RERANKER_ERROR` in production, before/after ranking telemetry, and evaluation hooks (`EvaluationRunConfig` may disable rerank).

### Phase 11 — Context Builder and Evidence Contract

Construct the generation context within configurable token/evidence budgets, preserve source provenance, assign request-scoped evidence IDs such as `E1`, `E2`, `E3`, and prevent arbitrary citation identities from reaching the model.

### Phase 12 — Grounded Generation

Implement provider-neutral generation, strict evidence-only prompting, structured answer/citation output, insufficient-evidence behavior, provider error handling, latency/token telemetry, and document prompt-injection protections.

### Phase 13 — Citation Mapping and Validation

Map request-scoped evidence IDs to authoritative chunks/pages, fail closed on invented IDs (`CITATION_VALIDATION_FAILED`), validate collection/document/page relationships, and render public citations without `chunk_id`.

### Phase 14 — No-Answer Decision Policy

Implement explicit insufficient-evidence decision points and distinguish legitimate no-answer results from infrastructure/provider failures.

### Phase 15 — End-to-End Query API

Wire authorization, retrieval, fusion, reranking, context building, generation, citation validation, error translation, response metadata, and correlation IDs into the public query endpoint.

### Phase 16 — Document Deletion and Index Consistency

Implement safe deletion/tombstoning after index phases (not blocked on the query API), retrieval artifact cleanup, source PDF cleanup policy, version consistency, retryable cleanup jobs, and tests preventing orphan searchable chunks. Query-race tests wait until Phase 15.

### Phase 17 — Observability

Standardize structured logging, tracing, and metrics. Phases 03–15 already emit stage spans for the capability they add; this phase completes naming, redaction, and dashboards. Do not treat this as the first telemetry.

### Phase 18 — Security Hardening

Harden the API-key and collection-ownership controls introduced in Phases 00/02. Add resource limits, MIME/file validation hardening, secret handling, untrusted-document protections, cross-collection leakage tests, and abuse controls. Do not introduce authentication here for the first time.

### Phase 19 — Evaluation Harness

Implement the versioned golden dataset schema and reusable evaluation runners for parsing/provenance, retrieval, reranking, answer quality, citation quality, no-answer behavior, and adversarial cases.

### Phase 20 — RAG Quality Experiments

Benchmark and compare dense-only, sparse-only, hybrid, and hybrid-plus-reranking configurations. Capture Recall@K, MRR, nDCG where useful, citation metrics, faithfulness, latency, and cost.

### Phase 21 — Production Failure Scenarios

Exercise corrupt PDFs, provider failures, partial indexing, queue failures, no results, reranker timeout, generation timeout, citation fabrication, deletion races, prompt injection, and cross-collection protection.

### Phase 22 — Docker, CI, and Deployment Readiness

Finalize local Docker topology, migrations, service readiness, CI tests/lint/type checks, configuration validation, reproducible startup, and deployment guidance.

### Phase 23 — Documentation, Learning, and Interview Readiness

Finalize README, architecture explanation, operational docs, learning path, concept notes, scenarios, interview Q&A, benchmarks, and portfolio walkthrough.

---

## 9. Phase Dependency Map

```text
Phase 00 Foundation
       ↓
Phase 01 Domain + Persistence
       ↓
Phase 02 Upload + Storage + Lifecycle
       ↓
Phase 03 Async Ingestion
       ↓
Phase 04 Parsing
       ↓
Phase 05 Chunking
       ↓
Phase 06 Dense index
(named vectors created)
      /         \
     v           v
Phase 08        Phase 07
Dense retrieve  Sparse index + retrieve
(from 06)       + READY finalize
     \           /
      v         v
Phase 09 Hybrid Retrieval + RRF
       ↓
Phase 10 Reranking
       ↓
Phase 11 Context + Evidence IDs
       ↓
Phase 12 Grounded Generation
       ↓
Phase 13 Citation Validation
       ↓
Phase 14 No-Answer Policy
       ↓
Phase 15 End-to-End Query API

Phase 16 Deletion Consistency
  depends on 02, 03, 06, 07
  (query-race tests after 15)

Phase 17 Observability
  depends on 03, 15
  (standardizes spans those phases already emit)
       ↓
Phase 18 Security
       ↓
Phase 19 Evaluation Harness
       ↓
Phase 20 Quality Experiments
       ↓
Phase 21 Failure Scenarios
       ↓
Phase 22 Docker + CI + Deployment
       ↓
Phase 23 Documentation + Learning
```

Some phases may be developed partially in parallel where dependencies permit, but an agent must not skip prerequisite contracts simply because implementation can technically compile.

---

## 10. Cross-Cutting Rules

### Provenance

Every chunk must remain traceable to:

```text
collection_id
  → document_id
  → document_version
  → page_number
  → chunk_id
```

This must survive all online and evaluation flows.

### Provider Boundaries

Core domain/services must not directly depend on provider SDKs.

Use adapters for:

- PDF parsing;
- object storage;
- embeddings;
- retrieval store;
- reranking;
- generation;
- queue infrastructure.

### Configuration

Do not hardcode environment-specific values such as:

- model names;
- embedding dimensions;
- top-K;
- candidate counts;
- chunk size/overlap;
- context budgets;
- timeouts;
- storage buckets;
- provider endpoints.

Configuration changes that materially alter evaluation behavior must be versionable/reproducible.

### Security

- retrieved PDF text is untrusted;
- collection filters must be applied at retrieval time;
- secrets must never be committed;
- sensitive raw document/query content must not be logged by default;
- citations must never cross collection boundaries.

### Money / Tokens / Latency

Where generation or hosted models are used, record enough metadata to evaluate token usage, latency, and later cost without coupling business logic to one provider.

---

## 11. Testing Strategy

Testing is part of each phase, not a final activity.

### Unit Tests

Cover deterministic domain behavior such as:

- lifecycle transitions;
- chunk metadata construction;
- RRF;
- candidate deduplication;
- evidence-ID mapping;
- citation validation;
- no-answer decision rules;
- configuration validation.

### Contract Tests

Cover provider/storage adapters against stable internal interfaces.

### Integration Tests

Cover:

- PostgreSQL repositories;
- Qdrant indexing/filtering;
- queue/worker behavior;
- upload-to-READY flow;
- retrieval pipeline;
- deletion cleanup.

### End-to-End Tests

Cover at minimum:

```text
Upload PDF
→ READY
→ Ask question
→ Retrieve evidence
→ Generate answer
→ Validate citations
→ Return document/page citations
```

Also cover:

```text
Upload PDF
→ Ask unsupported question
→ INSUFFICIENT_EVIDENCE
→ zero fabricated citations
```

### Evaluation Tests

Use the golden dataset to catch quality regressions that unit/integration tests cannot detect.

---

## 12. Required Production Failure Scenarios

The implementation must explicitly test or simulate at least:

1. corrupt PDF;
2. password-protected PDF;
3. extraction-empty PDF;
4. parser crash;
5. embedding timeout/failure;
6. retrieval-store unavailable;
7. sparse indexing failure;
8. partial indexing;
9. duplicate upload;
10. worker retry after partial work;
11. no retrieval results;
12. dense/sparse partial retrieval failure;
13. reranker timeout;
14. generation timeout/rate limit;
15. context exceeds configured budget;
16. LLM returns unknown evidence ID;
17. LLM attempts invented document/page citation;
18. prompt injection contained inside PDF;
19. cross-collection retrieval attempt;
20. document deletion during/after ingestion;
21. orphan search artifacts;
22. database state update fails after index write.

Expected behavior for each scenario must be documented in the relevant phase file.

---

## 13. Evaluation Gates

The project must demonstrate measurable comparisons between:

```text
Dense only
Sparse only
Hybrid
Hybrid + reranking
```

Required metric families include:

- Recall@K;
- Precision@K where useful;
- MRR;
- nDCG where useful;
- answer relevance;
- groundedness/faithfulness;
- unsupported claim rate;
- citation validity;
- citation correctness;
- citation completeness;
- no-answer precision/recall;
- false-answer rate;
- stage latency;
- model token/cost metadata where available.

Do not invent release thresholds before a real baseline has been measured.

---

## 14. Coding Agent Execution Rules

Before implementing any phase:

1. Read this `Implementation.md`.
2. Read the relevant `implementation/phase-XX-*.md` file.
3. Read the referenced PRD/HLD/LLD/ADR/evaluation documents.
4. Confirm prerequisite phases are complete or identify the exact dependency being stubbed.
5. List the files expected to change.
6. List required tests before writing implementation code.
7. Do not implement future phases opportunistically.
8. Do not change architecture silently.
9. If architecture must change, create/update an ADR first.
10. Keep provider-specific code behind adapters.
11. Run required verification.
12. Update the phase status only after evidence supports the status.
13. Update relevant learning/documentation material before marking a phase `COMPLETE`.

---

## 15. Definition of Done for Every Phase

A phase may be marked `COMPLETE` only when:

- intended functionality is implemented;
- required unit/integration tests pass;
- failure scenarios relevant to that phase are tested;
- architecture rules are preserved;
- security implications are reviewed;
- observability is added where applicable;
- no unresolved TODO silently changes product behavior;
- documentation is updated;
- learning notes explain what was built and why;
- code review/architecture review is complete where required.

---

## 16. Learning-First Requirement

This repository is both an implementation and a learning system.

For every major concept, `Learning/` should eventually explain:

- what the concept is;
- why this project uses it;
- alternatives considered;
- trade-offs;
- production failure modes;
- how it is implemented here;
- how to test/evaluate it;
- likely interview questions.

Expected learning areas include:

- PDF parsing;
- chunking;
- embeddings;
- vector databases;
- sparse retrieval;
- hybrid retrieval;
- RRF;
- reranking;
- provenance;
- grounded generation;
- citation validation;
- RAG evaluation;
- prompt injection;
- async ingestion;
- idempotency;
- observability;
- production failure handling.

---

## 17. Review Gates Before Coding

Before Phase 00 production implementation begins, complete the architecture review gate and ADR-011 freeze:

- review PRD vs HLD consistency;
- review HLD vs LLD consistency;
- review ADR status and unresolved choices;
- verify architecture diagrams match HLD/LLD;
- verify evaluation strategy can observe required intermediate outputs;
- review security boundaries;
- review failure scenarios;
- review phase dependency map;
- verify no critical design decision exists only implicitly.

Any major contradiction must be resolved before coding.

---

## 18. Step 7 Exit Criteria

Step 7 is complete when:

- this master implementation plan is reviewed;
- the phase sequence is accepted;
- dependencies are understandable;
- cross-cutting architecture rules are explicit;
- every later phase can reference one authoritative execution roadmap;
- no application implementation has started prematurely.

The next planning step is Step 8: create `implementation/README.md` and the detailed phase-by-phase implementation files.
