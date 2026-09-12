# Phase 13 — Citation Mapping and Validation

## Validity vs semantic correctness

Validity: every cited `E#` was in this request’s evidence map, the chunk belongs to the collection, and the version is still searchable. The public citation is filled from PostgreSQL provenance, never from model-written page numbers. Semantic correctness (does E1 actually support the claim?) is an evaluation metric, not a V1 runtime check.

## Why the application owns mapping

If the model emits “page 17”, we cannot prove that page is in this collection. `E1 → chunk_id → document/version/page` is deterministic. Invented IDs fail the request with `CITATION_VALIDATION_FAILED`. V1 does not strip the bad ID and return a partial `ANSWERED` response.
