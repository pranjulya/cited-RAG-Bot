# Phase 23 — Documentation and Interview Readiness

The path from PDF page to validated citation is: durable Postgres provenance, derived Qdrant indexes, collection-scoped retrieve, RRF, rerank, E-IDs, grounded generate, fail-closed validation.

Hybrid retrieval exists because dense and sparse fail on different questions. Reranking exists because recall lists are noisy. Evaluation is layered so we do not swap the LLM for a retrieval miss. No-answer exists so unsupported questions do not become fluent fiction. The main production tradeoff is fail-closed latency vs silent degraded answers — V1 chooses fail-closed.

Measured golden-v1 scores live in `reports/v1-defaults.md` and `evaluation/results/matrix.json`. Reproduce with `python -m cited_rag.evaluation --matrix`. Dense-only loses rank (MRR 0.250 vs 0.500); hybrid+rerank matches sparse on this lexical fixture and remains the production path.
