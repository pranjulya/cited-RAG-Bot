# Phase 08 — Dense Retrieval

## What does Recall@K measure?

Recall@K is the share of relevant pages that appear anywhere in the top K retrieved chunks. First-stage dense search is judged on whether the right evidence showed up at all, not whether it sat at rank 1. Precision and citation quality are later stages.

## Why first-stage retrieval optimizes recall before precision

A missed chunk can never be reranked or cited. Over-retrieving a few extra neighbors is cheaper than a silent miss. Top-K (`CITED_RAG_RETRIEVAL_TOP_K`) is therefore a recall knob, not a final answer size. Phase 09–11 will fuse, rerank, and budget evidence.

## Why collection filtering happens inside retrieval

The application uses one Qdrant collection. RAG collections are payload filters. If the ANN search runs unfiltered and the API trims afterward, another collection’s vectors still influence neighbors and can leak across tenants. Filters for `collection_id` **and** `document_version_id IN (active READY versions)` are applied in the store query, not after it. Empty READY sets return no hits; they are not a 5xx.
