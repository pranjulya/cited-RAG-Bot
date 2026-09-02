# Step 9 — Architecture Review Gate

**Project:** Cited RAG Bot  
**Status:** PASSED  
**Version:** 1.0  
**Scope:** Pre-implementation architecture consistency, security, failure-mode, and evaluation review

---

## 1. Purpose

This review validates that the PRD, ADRs, HLD, architecture diagrams, evaluation strategy, LLD, `Implementation.md`, and phase plans are sufficiently consistent to allow implementation to begin without known architecture blockers.

This is not a code review. No application code exists yet.

---

## 2. Review Result

**Decision: PASS WITH IMPLEMENTATION GUARDRAILS**

No architectural contradiction was found that requires redesign before Phase 00.

The main pre-coding blocker was governance rather than design: the ADR index still marked all core decisions as `Proposed` even though HLD, LLD, and implementation planning depended on them. Step 9 resolves that by freezing the accepted architecture directions in `docs/architecture/decisions/README.md`.

Some technology parameters remain intentionally configurable and evaluation-driven. They are not architecture blockers.

---

## 3. Frozen Architecture

```text
Client
  ↓
FastAPI
  ├── PostgreSQL        authoritative metadata/provenance
  ├── Object Storage    original PDFs
  └── Redis Queue       ingestion coordination
          ↓
       Worker
          ↓
       Docling
          ↓
   page-aware chunks
          ↓
 Dense + Sparse Index
          ↓
        Qdrant

Query
  ↓
Dense Retrieval ────────┐
                         ├── RRF
Sparse Retrieval ───────┘
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
               Answer + Page Citations
```

The architecture invariants are:

1. PostgreSQL is the durable provenance source of truth.
2. Qdrant is rebuildable derived retrieval state.
3. Source PDFs are retained until document/version deletion.
4. Ingestion is asynchronous.
5. Retrieval is always collection-scoped.
6. Dense and sparse retrieval are mandatory V1 paths.
7. RRF is the initial hybrid fusion strategy.
8. Reranking occurs before context construction.
9. The application generates citation/evidence identities.
10. The model never invents trusted page/document identity.
11. Citation validation occurs before response delivery.
12. Unsupported questions may legitimately return `INSUFFICIENT_EVIDENCE`.
13. Retrieved PDF text is untrusted data.
14. Providers/infrastructure are accessed through adapters.
15. Quality is measured through a versioned golden dataset.

---

## 4. Contradiction Review

### PRD vs HLD

Result: **PASS**

The HLD preserves the PRD requirements for PDF-only ingestion, multi-document collections, page provenance, hybrid retrieval, reranking, citation validation, no-answer behavior, security, observability, and evaluation.

### HLD vs LLD

Result: **PASS**

The LLD refines the HLD into module boundaries, domain contracts, persistence ownership, provider interfaces, evidence IDs, citation validation, lifecycle states, and failure taxonomy without changing the system boundaries.

### Evaluation Strategy vs Runtime Architecture

Result: **PASS**

The runtime architecture exposes dense, sparse, fused, and reranked candidate stages independently enough to support the required offline comparisons and root-cause analysis.

### Implementation.md vs Detailed Phase Plans

Result: **PASS WITH GUARDRAIL**

The phase plans align with the master implementation sequence. Cross-cutting concerns such as security, observability, and evaluation must not be postponed simply because dedicated hardening phases occur later.

---

## 5. Important Review Corrections

### Correction 1 — Observability cannot begin only in Phase 17

Phase 17 is the observability **hardening and completion** phase.

Earlier phases must already emit the telemetry required to understand their behavior. For example:

- ingestion phases emit job/stage status and classified failures;
- retrieval phases expose candidate counts and latency;
- reranking exposes before/after ranking metadata;
- generation captures latency/token metadata;
- citation validation records validation failures.

Phase 17 standardizes and completes this instrumentation.

### Correction 2 — Security cannot begin only in Phase 18

Phase 18 is the security **hardening** phase.

Security requirements apply from the first relevant implementation phase:

- file validation during upload;
- collection filters during retrieval;
- secret-safe configuration in foundation;
- untrusted document handling during parsing/generation;
- citation authorization during validation;
- safe logging in every phase.

### Correction 3 — Evaluation hooks cannot wait until Phase 19

Phase 19 builds the reusable evaluation harness, but Phases 04–15 must expose deterministic intermediate outputs that the harness can later consume.

Do not build retrieval/reranking logic as opaque methods that prevent offline replay or inspection.

### Correction 4 — Retrieval degradation must be explicit

V1 uses fail-closed behavior when a mandatory dense or sparse retrieval dependency fails.

Do not silently fall back to dense-only or sparse-only answers. This prevents online behavior from drifting away from the evaluated architecture.

### Correction 5 — READY means fully searchable

A document version may reach `READY` only after all mandatory V1 indexing artifacts are available.

A PostgreSQL status update is not sufficient evidence of readiness by itself.

---

## 6. Overengineering Review

### Accepted complexity

The following additional infrastructure is justified:

- PostgreSQL for durable domain/provenance state;
- Qdrant for hybrid retrieval experimentation;
- Redis-backed async worker boundary for ingestion;
- object storage for retained source PDFs.

These directly support the learning and production goals of the project.

### Complexity intentionally rejected for V1

Do not add without a new ADR:

- Elasticsearch/OpenSearch as a second lexical engine;
- Kafka/event streaming;
- Kubernetes;
- service mesh;
- multi-region deployment;
- OCR pipeline as guaranteed support;
- graph database;
- agentic orchestration framework;
- full user/organization IAM platform;
- separate microservices for each RAG stage.

The system should begin as a modular application plus worker, not a distributed microservice estate.

---

## 7. Security Review

Required controls before production-readiness can be claimed:

1. API-key authentication for portfolio V1.
2. Collection scope enforced server-side.
3. Collection/document filters applied at retrieval query time, not only post-filtered.
4. PDF MIME/signature/size validation.
5. parser resource limits and controlled failures.
6. source PDFs treated as untrusted.
7. prompt-injection tests using malicious text inside PDFs.
8. secrets excluded from repository and logs.
9. raw PDF/query content not logged by default.
10. generated citation IDs validated against request-scoped evidence.
11. deletion removes or invalidates searchable artifacts.
12. rate/resource controls before public deployment.

Security result: **PASS FOR DESIGN**, implementation evidence required later.

---

## 8. Failure-Mode Review

The existing design covers the important failure classes:

- corrupt/password-protected/extraction-empty PDF;
- parsing failure;
- embedding failure;
- partial index write;
- worker retry;
- Qdrant unavailable;
- one retrieval path unavailable;
- no retrieval results;
- reranker timeout;
- generation timeout/rate limit;
- excessive context;
- fabricated/unknown evidence ID;
- document prompt injection;
- cross-collection access;
- deletion/index cleanup race;
- database status failure after external index write.

Implementation rule: retries must be bounded and reason-aware. Do not wrap the entire RAG pipeline in one generic retry policy.

Failure-mode result: **PASS**.

---

## 9. Evaluation Review

The evaluation architecture correctly separates:

```text
Parsing / Provenance
Retrieval
Reranking
Answer Grounding
Citation Quality
No-Answer / Safety
```

Required comparisons remain:

```text
Dense only
Sparse only
Hybrid
Hybrid + reranking
```

No arbitrary release metric thresholds will be invented before the first reproducible baseline.

Evaluation result: **PASS**.

---

## 10. Decisions Intentionally Left as Configuration/Evaluation Variables

The following do not block Phase 00:

- exact embedding model;
- exact sparse encoder;
- chunk size/overlap;
- dense top-K;
- sparse top-K;
- RRF parameters;
- reranker model;
- final evidence count;
- context token budget;
- generation model;
- no-answer thresholds;
- release metric thresholds.

These must be configurable and captured in evaluation run metadata so experiments are reproducible.

---

## 11. Pre-Implementation Gate

Phase 00 may begin only if the implementer agrees to these rules:

- read `Implementation.md` and the current phase file first;
- do not change accepted architecture silently;
- use TDD for deterministic behaviors;
- keep provider SDKs in adapters;
- preserve provenance from the first domain model onward;
- add telemetry as each capability is implemented;
- apply security requirements in the phase where they become relevant;
- do not implement future phases opportunistically;
- update learning documentation as concepts become real;
- create/supersede an ADR when architecture evidence requires a change.

---

## 12. Step 9 Exit Criteria

- [x] PRD/HLD/LLD consistency reviewed.
- [x] Architecture decisions frozen.
- [x] Evaluation strategy reviewed against runtime boundaries.
- [x] Phase dependency model reviewed.
- [x] Security requirements reviewed.
- [x] Production failure modes reviewed.
- [x] Overengineering risks reviewed.
- [x] Cross-cutting phase-order risks documented.
- [x] No known architecture blocker remains before Phase 00.

**Final Step 9 decision: APPROVED TO PREPARE PHASE 00.**

This approval does not mean Phase 00 implementation has started. Step 10 must first establish implementation readiness and agent execution rules.
