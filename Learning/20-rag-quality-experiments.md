# Phase 20 — RAG Quality Experiments

## Why better Recall@K can still yield a worse answer

Recall only asks whether the page appeared in the fused list. If rerank then drops it, or the context budget cuts it, or the model cites `E99`, the user still sees a bad answer. Always pair retrieval metrics with citation validity and no-answer rate.

## Latency and cost vs rerank

A cross-encoder scores every fused candidate. Top-K 50 is much more expensive than 10. Measure MRR lift against p95 latency before raising `CITED_RAG_RERANK_TOP_N`.

## Why keep a simple baseline

Dense-only and sparse-only ablations (`EvaluationRunConfig`) show whether hybrid is earning its complexity. If sparse-only already recovers identifiers, hybrid still needs to prove it does not hurt that path.
