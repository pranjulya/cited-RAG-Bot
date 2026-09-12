# V1 configuration defaults

Measured on `evaluation/golden/v1.json` with hash embeddings and the heuristic generator (`python -m cited_rag.evaluation` and `run_v1_matrix`). Ablations are isolated via `EvaluationRunConfig`. These numbers are fixture-scale, not a hosted-model bake-off.

Recommended production path until a hosted encoder/reranker is measured:

- retrieval: dense + sparse, in-process RRF (`CITED_RAG_RRF_K=60`)
- rerank: on (`CITED_RAG_RERANK_TOP_N=10`)
- context: `CITED_RAG_MAX_EVIDENCE_ITEMS=8`, `CITED_RAG_CONTEXT_TOKEN_BUDGET=1500`
- no-answer: `CITED_RAG_MIN_RERANK_SCORE=0` until evaluation sets a baseline

Do not optimize Recall@K in isolation: a higher K can still produce a worse cited answer if rerank buries the page or generation invents IDs.
