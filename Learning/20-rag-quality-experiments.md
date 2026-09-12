# Phase 20 — RAG Quality Experiments

## Why better Recall@K can still yield a worse answer

Recall only asks whether the page appeared in the fused list. If rerank then drops it, or the context budget cuts it, or the model cites `E99`, the user still sees a bad answer. Always pair retrieval metrics with citation validity and no-answer rate.

## Latency and cost vs rerank

A cross-encoder scores every fused candidate. Top-K 50 is much more expensive than 10. Measure MRR lift against p95 latency before raising `CITED_RAG_RERANK_TOP_N`.

## Why keep a simple baseline

Dense-only and sparse-only ablations (`EvaluationRunConfig`) show whether hybrid is earning its complexity. If sparse-only already recovers identifiers, hybrid still needs to prove it does not hurt that path.

On golden-v1 (`python -m cited_rag.evaluation --matrix`): dense-only Recall@5=1.000 but MRR=0.250 / nDCG@5=0.815; sparse-only, hybrid, and hybrid-rerank all score MRR=0.500 / nDCG@5=1.000 with citation_validity=1.000 and false_answer=0.000. The fixture is a lexical policy sentence, so sparse already wins rank. Hybrid+rerank stays the V1 default because paraphrase questions still need dense, and the ablation does not regress the lexical path.
