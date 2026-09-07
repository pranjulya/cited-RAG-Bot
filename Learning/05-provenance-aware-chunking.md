# Phase 05 — Provenance-Aware Chunking

## Why chunking affects recall

Retrieval ranks chunks, not pages. Too large and a relevant sentence is diluted. Too small and the chunk lacks the words the query uses. Overlap is a hedge: a split that would have cut a sentence still appears in two neighbors. Evaluation later measures this; the numbers are settings, not frozen architecture.

## Why fixed-size chunks are not universally optimal

A heading plus one sentence and a 3,000-character paragraph are not the same unit. Character windows are a deterministic V1 baseline. Semantic splits can be compared later. V1 still splits **inside a page** so a citation can name one PDF page. Cross-page chunks are allowed only with explicit `page_start`/`page_end`; this phase does not merge pages.

## Why chunk configuration belongs in evaluation metadata

`CITED_RAG_CHUNK_TARGET_CHARS` and `CITED_RAG_CHUNK_OVERLAP_CHARS` change the retrieval unit. A golden set scored against one window size is not comparable to another. The strategy, target, and overlap used for a version are stored on `document_versions.chunking_config` so later evaluation can reproduce that version without reading logs. Chunk IDs are UUIDv5 of version, page range, order, and text hash so a rerun with the same bytes and config reproduces the same identities (those IDs become Qdrant `point_id` later).
