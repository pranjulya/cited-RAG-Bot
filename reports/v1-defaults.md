# V1 configuration defaults

These defaults are **wiring defaults**, not quality winners. Unit experiments run hash embeddings and a heuristic generator on `evaluation/golden/v1.json`. They prove dense-only, sparse-only, hybrid, and hybrid+rerank ablations are isolated via `EvaluationRunConfig`. They do not justify changing ADR-011.

Recommended production path until a hosted encoder/reranker is measured:

- retrieval: dense + sparse, in-process RRF (`CITED_RAG_RRF_K=60`)
- rerank: on (`CITED_RAG_RERANK_TOP_N=10`)
- context: `CITED_RAG_MAX_EVIDENCE_ITEMS=8`, `CITED_RAG_CONTEXT_TOKEN_BUDGET=1500`
- no-answer: `CITED_RAG_MIN_RERANK_SCORE=0` until evaluation sets a baseline

Do not optimize Recall@K in isolation: a higher K can still produce a worse cited answer if rerank buries the page or generation invents IDs.
