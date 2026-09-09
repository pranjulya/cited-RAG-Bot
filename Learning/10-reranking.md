# Phase 10 — Reranking

## Why rerank after broad retrieval?

Hybrid RRF optimizes recall: it pulls in dense paraphrases and sparse identifiers, then mixes ranks. That list is still noisy. A reranker scores the query against each remaining passage and keeps a shorter, higher-precision shortlist for the context builder. Missing a chunk at retrieval cannot be fixed here; reranking only reorders what fusion already found.

## Cross-encoder vs embedding similarity

Bi-encoders (dense retrieval) embed the query and the passage separately, then compare vectors. That is fast enough for the whole index. A cross-encoder reads the query and the passage together and outputs a relevance score. It is slower and usually more precise, so it only runs on the fused shortlist. V1 production can swap a local cross-encoder behind `Reranker` without changing orchestration. Tests and local dev use `lexical-overlap` so CI does not download a model.

## Why reranking is not automatically an improvement?

A weak reranker can bury the right chunk. Latency and cost go up either way. Evaluation must compare fused order vs reranked order (MRR/nDCG) with `EvaluationRunConfig.include_rerank`. Production never skips rerank on timeout: that is `RERANKER_ERROR`, not a silent return of fused ranks.
