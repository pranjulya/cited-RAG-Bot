# ADR-011 — V1 Locked Implementation Policies

**Status:** Accepted  
**Decision:** Freeze the unresolved V1 contracts that Step 9 left implicit so implementation cannot invent a different product depending on which document is read.

## Context

Step 9 marked the ADR **index** Accepted while individual ADR files remained Proposed, and HLD/LLD still listed “lock before coding” items. A review of PRD, ADRs, HLD, LLD, diagrams, evaluation strategy, and phase plans found real contradictions on lifecycle, versioning, READY filtering, Qdrant schema, auth, citations, retrieval failure, and phase ownership.

This ADR is the single freeze for those items. If implementation evidence requires a change, supersede this ADR (or the specific ADR it extends). Do not silently diverge in phase files.

## Locked Policies

### 1. Package layout

All application code lives under `src/cited_rag/`:

```text
src/cited_rag/
├── api/
├── application/
├── domain/
├── ports/
├── adapters/
├── workers/
├── observability/
└── config/
```

Phase 00 creates `main.py`, `config.py`, and `api/health.py` inside this package. Later phases fill the LLD modules under the same root (`config/settings.py` and `api/routes/` may be added then). Do not use a top-level `src/api` tree. Do not create a second package root.

### 2. Lifecycle

Canonical document-version states:

```text
UPLOADED → QUEUED → PROCESSING → READY
                              ↘ FAILED
FAILED → QUEUED                 # explicit retry
READY → DELETING → DELETED
```

- Upload persists the source PDF, creates the version as `UPLOADED`, enqueues the job, then the version is `QUEUED` before the `202` response.
- Upload `202` status is `QUEUED`.
- Phase 03 worker claims the job and transitions `QUEUED → PROCESSING`.
- `READY` is set only after PostgreSQL provenance **and** both dense and sparse Qdrant artifacts exist for that version.
- `FAILED` is never searchable.
- `DELETING` is not searchable. Cleanup is retryable until `DELETED`.

PRD FR-03 status names are a product subset. The implementation state machine above is authoritative.

### 3. Duplicate and versioning policy

- Content-hash uniqueness is **per collection**, among non-deleted versions. The same PDF may exist in two collections.
- `POST /v1/collections/{collection_id}/documents` without `document_id`:
  - if an active (non-deleted) document in that collection already has this `content_hash`, return that document/version (idempotent); do not create a second searchable copy;
  - otherwise create a new document and version `1`.
- `POST /v1/collections/{collection_id}/documents/{document_id}/versions` creates version `N+1` of an existing document **only when the bytes are new** for that collection.
- If the uploaded `content_hash` already exists on a non-deleted version in the same collection, do not create `N+1`. Return the existing document/version. Same bytes never produce a second copy inside one collection.
- If that existing version is `FAILED`, do not create a new document. Retry is `FAILED → QUEUED` (re-enqueue), not a second upload identity.
- `active_version_id` points at the version currently intended for retrieval.
- Only the **active READY** version of a document is searchable.
- A previous READY version remains in PostgreSQL for audit/reprocess but is excluded from retrieval once a newer version becomes the active READY version.
- `active_version_id` is set to the new version only when that version reaches `READY`. While version `N+1` is processing, version `N` (if READY) remains searchable.

### 4. Retrieval failure vs empty results

Production V1 is fail-closed for **operational** dense or sparse retrieval failure (`DENSE_RETRIEVAL_ERROR` / `SPARSE_RETRIEVAL_ERROR`). Do not ship `ALLOW_SINGLE_RETRIEVER` as a production default. A future degraded mode requires a new ADR and evaluation evidence.

Empty candidate lists are not failures. If one retriever returns zero hits and the other succeeds, fuse the surviving list.

Evaluation ablations (dense-only, sparse-only, hybrid without rerank) use an explicit `EvaluationRunConfig` that disables stages. That config is **not** the production query policy.

### 5. Qdrant hybrid schema

- One Qdrant collection for the application (not one Qdrant collection per RAG collection).
- Each point identity is the chunk UUID (`point_id` is a UUID, never a free-form string).
- Named vectors on the **same** point: `dense` and `sparse`.
- Phase 06 **creates** the collection with both named vectors even if sparse values are populated in Phase 07. Phase 07 updates the same point; it does not create a second identity.
- Payload (indexed where used as a filter):

```text
collection_id
document_id
document_version_id
page_start
page_end
chunk_order
index_version
```

- Authoritative chunk text lives in PostgreSQL. Qdrant may copy text into payload for rerank/latency; if copied, ingestion must keep it consistent with PostgreSQL.
- Every retrieval query applies, inside Qdrant, `collection_id` **and** `document_version_id IN (active READY versions for this request)`. PostgreSQL is the source of the READY/active set. Collection-only filters are a security defect.
- Points may exist for a processing version; they must not match the READY version-id filter.

### 6. Ingestion write order and READY ownership

```text
persist pages/chunks in PostgreSQL
  → embed dense
  → encode sparse
  → upsert both named vectors on the chunk UUID
  → verify dense + sparse completeness
  → set READY and active_version_id
```

Do not upsert Qdrant before durable page/chunk rows exist.

Phase 03 owns queue, lease, `QUEUED → PROCESSING`, retries, and `FAILED`. It must not mark `READY`.

Phase 06 owns dense named-vector upserts.

Phase 07 owns sparse named-vector upserts **and** the ingestion-finalize completeness check that transitions `PROCESSING → READY` (or `FAILED` if sparse/dense artifacts are incomplete).

### 7. Sparse encoder

Add a `SparseEncoder` port. V1 default adapter: FastEmbed BM42 (or the documented equivalent sparse encoder) producing Qdrant sparse vectors at ingest and query time.

Native Qdrant BM25 may be compared later behind the same port. A second lexical engine (OpenSearch/Elasticsearch) remains out of scope.

Encoder name/version must be recorded on evaluation runs. Corpus-dependent scoring, if any, is part of run metadata.

### 8. Fusion

RRF is computed **in application code** (`FusionStrategy` in `application/retrieval/fusion.py`). Do not use Qdrant native fusion for the V1 online path; independent dense and sparse lists must remain observable for evaluation.

### 9. Reranker failure

Production default: reranker operational timeout/failure fails the query (`RERANKER_ERROR`). Do not silently return fused order.

Evaluation may disable reranking through `EvaluationRunConfig`. That is a different configuration, not a hidden production fallback.

Preferred V1 adapter: local cross-encoder behind `Reranker`. Hosted adapters may be added without changing orchestration.

### 10. Citation contract

**Model-visible evidence** is:

```text
[E1]
Evidence:
"<chunk text>"
```

Do not send `document_id`, `chunk_id`, or page numbers to the model. Provenance stays in the server-side evidence map.

**External citation object:**

```json
{
  "document_id": "uuid",
  "document_version_id": "uuid",
  "document_name": "handbook.pdf",
  "page_start": 17,
  "page_end": 17
}
```

Do not expose `chunk_id` on the public API. Page-level citations are the product contract. Internal mapping remains `evidence_id → chunk_id → PostgreSQL provenance`.

If the model returns an unknown or unapproved evidence ID: fail the request with `CITATION_VALIDATION_FAILED`. V1 does not repair, strip-and-answer, or return `ANSWERED` with a subset of valid IDs after fabrication. `INSUFFICIENT_EVIDENCE` remains a valid generator status when the model abstains using only approved IDs.

### 11. Authentication and document routes

Portfolio V1 authentication: API key.

- Header: `Authorization: Bearer <api_key>`
- `Collection.owner_id` is the API principal id that created the collection.
- Every collection, document, and query operation authorizes that the principal owns (or is granted) the collection.
- `GET`/`DELETE /v1/documents/{document_id}` must load the document, authorize via `document.collection_id`, and return `404` for both missing and unauthorized documents (no IDOR via UUID guessing).
- API-key middleware exists from Phase 02 (skeleton in Phase 00 settings). Phase 18 hardens limits and adversarial tests; it does not introduce auth for the first time.

### 12. Worker / queue

Queue port remains provider-neutral. V1 adapter: **arq** on Redis.

- Job payload is `document_version_id` (and correlation id), never raw PDF bytes.
- Idempotency key is `document_version_id`.
- At-least-once delivery; retries are bounded and classified (transient vs permanent).
- Processing lease: only one active ingestion execution per document version.

### 13. No-answer ownership

- Phase 12: generator may emit structured `INSUFFICIENT_EVIDENCE`; it does not own policy thresholds.
- Phase 14: policy service decides abstention from empty retrieval, weak rerank/context, or model abstention. Provider/infrastructure errors are never mapped to `INSUFFICIENT_EVIDENCE`.
- Zero READY documents in a collection: `INSUFFICIENT_EVIDENCE` with reason `NO_READY_DOCUMENTS` (success-shaped no-answer, not a 5xx). Unauthorized collection remains `403`/`404`.

### 14. Chunking

V1 prefers single-page chunks. Cross-page chunks are allowed only with explicit `page_start`/`page_end`. Baseline configuration (size/overlap numbers) remains evaluation-driven.

### 15. Deletion timing

Tombstone + index purge can be implemented after Phases 02, 03, 06, and 07. Do not wait for the query API (Phase 15) to make documents non-searchable. Concurrent query/delete tests are added after Phase 15.

### 16. Observability, CI, and learning

- Phase 00: lint/type/unit CI, root README, `Learning/` stub, secret-safe settings, `/ready` documented skeleton.
- Phases that introduce Postgres, Redis, or Qdrant add those services to compose and integration CI.
- Each of Phases 03–15 emits the LLD stage spans/metrics for the capability it adds. Phase 17 standardizes; it is not the first telemetry.
- `Learning/<topic>.md` is updated in the phase that introduces the concept. Phase 23 indexes and polishes; it does not create Learning from scratch.

### 17. Evaluation observability

Per-question eval results must retain:

- dense, sparse, fused, and reranked candidate ids/ranks/scores;
- approved context evidence IDs and ids dropped by budget;
- generator status, claims/evidence IDs **before** validation;
- validator outcome;
- no-answer reason code;
- page-collapsed Recall@K/MRR (gold is page-level; retrieval unit is chunk);
- stage latencies including fusion, context, and citation validation.

nDCG is used only when graded labels exist. The first golden JSON uses ungraded page labels unless a graded field is added.

### 18. Still configuration / evaluation (not architecture)

Embedding model, chunk size/overlap numbers, top-K, RRF `k`, reranker model, evidence count, token budget, generation model, numeric no-answer cutoffs, and release metric thresholds remain configurable. Do not invent numeric SLOs before a baseline.

## Consequences

- HLD, LLD, PRD citation examples, diagrams, ADR bodies, evaluation strategy, `Implementation.md`, and phase files must match this ADR.
- `ALLOW_SINGLE_RETRIEVER` is not a V1 production policy.
- Phase 06 must not create a dense-only Qdrant collection.
- Coding agents must read this ADR with `Implementation.md` and the current phase file.

## Supersedes / extends

Extends ADR-001–010 by locking policies those ADRs left as “to decide” or “validation required.” Does not replace their core technology choices.
