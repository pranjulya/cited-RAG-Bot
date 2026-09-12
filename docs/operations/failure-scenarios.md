# Production failure scenarios

Every row must fail closed or abstain. Production has no silent dense-only/sparse-only fallback.

| Scenario | Expected |
|---|---|
| Corrupt / password / empty PDF | `PDF_PARSE_FAILED` / `PDF_PASSWORD_PROTECTED` / `PDF_UNSUPPORTED` |
| Embedding timeout | `EMBEDDING_FAILED` or transient ingestion retry |
| Qdrant down at ingest | `INDEX_UNAVAILABLE` / transient; version not READY |
| Qdrant down at query | `DENSE_RETRIEVAL_ERROR` / `SPARSE_RETRIEVAL_ERROR` 503 |
| One retriever empty hits | Fuse the other list |
| One retriever timeout | Fail closed, do not answer from the other |
| Reranker timeout | `RERANKER_ERROR` 503, not fused order |
| Generation timeout | `GENERATION_PROVIDER_ERROR` 503, not no-answer |
| Invented evidence ID | `CITATION_VALIDATION_FAILED` 422 |
| Zero READY docs | 200 `INSUFFICIENT_EVIDENCE` / `NO_READY_DOCUMENTS` |
| Prompt injection in PDF | Untrusted evidence; abstain unless tokens support the question |
| Cross-collection query | 404 |
| Delete then query | Tombstone first; version not in READY set |
| Partial index | READY blocked (`INDEX_INCOMPLETE`) |
