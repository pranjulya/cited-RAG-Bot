# Step 2 — Architecture Decision Workshop

**Project:** Cited RAG Bot  
**Status:** Accepted after Step 9 architecture review; V1 contracts frozen in ADR-011  
**Version:** 1.1

## Purpose

This folder records the architecture decisions that govern implementation of the Cited RAG Bot.

The PRD locks the product direction: PDF-only V1, multi-PDF collections, hybrid retrieval, reranking, grounded generation, page-level citations, citation validation, evaluation, observability, and controlled no-answer behavior.

The ADR index is the authoritative status registry for these decisions. Detailed ADR files contain the rationale and alternatives considered.

## Decision Principles

1. Citation provenance must survive every stage from PDF page to final answer.
2. Retrieval quality must be measurable, not assumed.
3. External providers must sit behind interfaces/adapters.
4. PostgreSQL owns durable application metadata; retrieval indexes are derived/searchable artifacts.
5. Long-running ingestion executes asynchronously.
6. Retrieved PDF content is untrusted data, never trusted instructions.
7. Failure of one retrieval component has explicitly defined behavior.
8. V1 is production-oriented without infrastructure that does not materially improve the learning or product goals.
9. Important provider choices remain replaceable without rewriting core domain logic.
10. Evaluation design is part of architecture, not a post-build activity.

## Accepted Decision Set

| ADR | Decision | Accepted Direction | Status |
|---|---|---|---|
| ADR-001 | PDF parsing | Docling primary parser with page provenance behind `DocumentParser` interface | Accepted |
| ADR-002 | Metadata persistence | PostgreSQL as durable system of record | Accepted |
| ADR-003 | Retrieval store | Qdrant for dense + sparse retrieval; PostgreSQL remains authoritative provenance store | Accepted |
| ADR-004 | Hybrid retrieval | Dense + sparse retrieval with Reciprocal Rank Fusion | Accepted |
| ADR-005 | Reranking | Replaceable reranker after hybrid candidate generation; local cross-encoder is preferred V1 default | Accepted |
| ADR-006 | Citation contract | Application-generated request evidence IDs; deterministic citation validation before response | Accepted |
| ADR-007 | Ingestion execution | Asynchronous worker through a Redis-backed queue abstraction | Accepted |
| ADR-008 | Original PDF storage | Object-storage abstraction; local filesystem in development and S3-compatible production adapter | Accepted |
| ADR-009 | Model/provider boundaries | Embedding, reranking, generation, parser, storage and retrieval infrastructure behind explicit adapters | Accepted |
| ADR-010 | Evaluation gates | Versioned golden dataset and retrieval/citation/no-answer regression gates | Accepted |
| ADR-011 | V1 locked policies | Lifecycle, versioning, Qdrant named vectors, READY filters, auth, citations, fail-closed, worker, eval ablations | Accepted |

Individual ADR files are **Accepted**. Do not treat leftover “Proposed” language in older revisions as license to redesign. ADR-011 wins on any remaining contradiction.

## Step 9 Frozen Policies

### Retrieval failure policy

V1 fails the query closed when a mandatory dense or sparse retrieval **dependency** fails. It must not silently return a degraded dense-only or sparse-only answer. One retriever returning **zero hits** is not a dependency failure; fuse the surviving list. A future degraded mode may be introduced only through a new ADR and evaluation evidence. Evaluation ablations use `EvaluationRunConfig`, not production degraded mode.

### Sparse retrieval implementation

Sparse retrieval remains inside the Qdrant retrieval boundary for V1. The collection schema uses named vectors `dense` and `sparse` on the same chunk UUID, created in Phase 06. V1 default encoder is FastEmbed BM42 behind `SparseEncoder`. Adding a second lexical search engine is out of scope unless evaluation demonstrates a material need.

### Reranking

Use a provider-neutral `Reranker` interface. Prefer a local cross-encoder for the baseline so the project can evaluate reranking independently of a hosted vendor. Hosted adapters may be added without changing orchestration. Production reranker failure is `RERANKER_ERROR`, not silent fused-order fallback.

### Source PDF retention

Retain the original PDF for the lifetime of the active document version. Deleting a document/version must schedule removal of source storage and derived retrieval artifacts according to the deletion consistency policy.

### Authentication boundary

Portfolio V1 uses API-key authentication (`Authorization: Bearer <api_key>`) and strict collection scoping. `Collection.owner_id` is the API principal. Document GET/DELETE authorize through `document.collection_id`. Full enterprise IAM, SSO, RBAC and multi-organization tenancy remain out of scope. The architecture must not make later user-level authorization impossible. Auth exists from Phase 02; Phase 18 hardens it.

### Evaluation thresholds

Metric families are frozen before implementation, but release thresholds are not fabricated. Establish the baseline first, inspect failures, then record numeric regression gates in the evaluation configuration.

## Architecture Constraints Derived From PRD

### PDF-only V1

Other document formats are deliberately excluded. Parser abstractions may support future extensions, but no implementation effort is spent on DOCX, HTML, URLs, or guaranteed OCR-heavy scanned documents in V1.

### Multi-document collections

Every retrieval operation is scoped to a collection. Every indexed evidence item preserves at minimum:

- `collection_id`
- `document_id`
- `document_version`
- `page_number`
- `chunk_id`
- `chunk_order`

Only the **active READY** document version is searchable.

### Citation integrity

The LLM is never trusted to invent document IDs, page numbers, or chunk IDs. The application owns citation identity and validation.

### Derived search indexes

Vector/sparse indexes are reconstructable from durable document/chunk metadata and the retained source PDF. They are never the sole provenance source of truth.

### Evaluation-first architecture

The architecture exposes intermediate retrieval/reranking results so the evaluation harness can measure each stage independently.

## Change Rule

These decisions are now frozen for implementation. If implementation evidence proves a decision unsuitable, create a new ADR or supersede the existing one before changing architecture. Do not silently alter provider boundaries, persistence ownership, citation identity, retrieval semantics, or ingestion execution.
