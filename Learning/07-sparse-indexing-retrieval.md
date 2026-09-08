# Phase 07 — Sparse Indexing and Retrieval

## Why vector search alone can fail

Dense embeddings group *similar meaning*. They often miss an exact identifier, a rare token, or a digit string that appears once. A query for `POLICY_42` should hit the chunk that contains those characters even if the surrounding prose is unlike the question.

## Dense vs sparse retrieval

Dense: one fixed-length vector per chunk; neighbors in that space are semantic. Sparse: a handful of term weights (BM25-style / BM42). The two lists are fused later (Phase 09). V1 stores both as named vectors on the **same** chunk UUID. Sparse does not create a second identity.

## Why exact identifiers often need lexical search

IDs, form numbers, and product codes are high-idf tokens. A character-hash or BM42 sparse encoder puts weight on those tokens so they can rank first. Tests use a deterministic lexical encoder; production V1 can switch to FastEmbed BM42 with `CITED_RAG_SPARSE_ENCODER_BACKEND=bm42`.

`READY` is set only after PostgreSQL chunks exist **and** both named vectors are present. Dense-only stays `FAILED` / non-searchable. Production sparse search filters `collection_id` and `document_version_id IN (active READY versions)`.
