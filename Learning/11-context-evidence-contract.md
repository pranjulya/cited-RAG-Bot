# Phase 11 — Context Builder and Evidence Contract

## Why E1/E2 instead of page numbers from the model?

The model only sees request-scoped labels (`E1`) and chunk text. Document, version, page, and chunk IDs stay in a server map. If the model invented “page 17”, we would have no way to know whether that page exists in this collection. After generation, the application looks up `E1` and renders the real page from PostgreSQL.

## What is the context builder trust boundary?

Everything before it (retrieval, fusion, rerank) is a recall/precision pipeline. Everything after it is generation. The builder is the last filter: only reranked, budgeted, approved text is formatted as data. System instructions never include PDF text, and PDF text never includes provenance the model could parrot.

## Why token budgeting matters

A larger context can raise recall of supporting sentences and also cost, latency, and distraction. Packing in rerank order until `CITED_RAG_MAX_EVIDENCE_ITEMS` or `CITED_RAG_CONTEXT_TOKEN_BUDGET` is hit keeps the prompt bounded. Chunks that do not fit are recorded as dropped for evaluation, not silently stuffed past the budget.
