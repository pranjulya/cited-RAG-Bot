# Phase 21 — Production Failure Scenarios

## Fail-open vs fail-closed

Fail-open would return a dense-only answer when sparse times out. That looks successful and is unevaluated. Fail-closed returns `SPARSE_RETRIEVAL_ERROR`. Empty hit lists still fuse because they are not dependency failures.

## Provider failure vs insufficient evidence

Timeouts and 5xx from Qdrant, the reranker, or the generator are operational. `INSUFFICIENT_EVIDENCE` is a successful abstention when the PDFs do not support the question. Mixing them hides outages as “we don’t know.”

## Compensating actions

Ingestion: retry transient errors; mark `FAILED` on permanent ones. Deletion: tombstone first, then retry index/storage purge. Never leave a READY version whose Qdrant points are gone, or a searchable version after `deleted_at`.
