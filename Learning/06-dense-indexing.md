# Phase 06 — Embedding and Dense Indexing

## What is an embedding?

An embedding is a list of numbers that stands in for text. Nearby vectors mean similar meaning for a trained model. This phase uses a deterministic hash backend so tests do not call a hosted model. The port is the same: `embed_documents` at ingest and `embed_query` for Phase 08. Swap the adapter when a real model is configured; do not scatter SDK calls in the worker.

## Why vector dimensions must match the index

Qdrant creates the `dense` named vector with a fixed size. A 32-dimensional point cannot live in a 1536-dimensional slot. The application rejects a batch whose lengths do not match `CITED_RAG_EMBEDDING_DIMENSION` instead of writing a corrupt index. Changing the model usually means a new `index_version` and a rebuild, not mixing sizes in one collection.

## Why metadata filters are a security requirement

The application has one Qdrant collection. RAG collections are payload fields, not separate indexes. A search that omits `collection_id` (and later, active READY `document_version_id`) can return another tenant's chunks. Filters are isolation, not just a way to make ANN faster. This phase stores those payload fields and payload indexes; product dense retrieval in Phase 08 must apply them.

Named vector `sparse` is created now and left empty. Phase 07 fills it on the same chunk UUID. The version stays `PROCESSING`. `READY` still requires both dense and sparse.
