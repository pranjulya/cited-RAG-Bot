# V1 configuration defaults

Measured on `evaluation/golden/v1.json` (2 cases: one answerable leave policy, one unanswerable) with hash embeddings, lexical sparse encoding, overlap rerank, and the heuristic generator.

Reproduce:

```bash
python -m cited_rag.evaluation
python -m cited_rag.evaluation --matrix
```

Artifacts: `evaluation/results/latest.json` (hybrid-rerank) and `evaluation/results/matrix.json`.

| Config | Recall@5 | MRR | nDCG@5 | Citation validity | No-answer P / R | False-answer | Latency (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|
| dense-only | 1.000 | 0.250 | 0.815 | 1.000 | 1.000 / 1.000 | 0.000 | 0 |
| sparse-only | 1.000 | 0.500 | 1.000 | 1.000 | 1.000 / 1.000 | 0.000 | 0 |
| hybrid | 1.000 | 0.500 | 1.000 | 1.000 | 1.000 / 1.000 | 0.000 | 0 |
| hybrid-rerank | 1.000 | 0.500 | 1.000 | 1.000 | 1.000 / 1.000 | 0.000 | 0 |

Dense-only recovers the policy page but ranks it worse (MRR 0.250 vs 0.500). Sparse, hybrid, and hybrid+rerank tie on this fixture because the answerable case is a lexical hit and the unanswerable case has no overlap. Latency rounds to 0 ms in-process. Tokens and $ cost are not billed by the heuristic generator.

These numbers are fixture-scale, not a hosted-model bake-off. They still support the ADR-011 production path until a hosted encoder/reranker is measured:

- retrieval: dense + sparse, in-process RRF (`CITED_RAG_RRF_K=60`)
- rerank: on (`CITED_RAG_RERANK_TOP_N=10`)
- context: `CITED_RAG_MAX_EVIDENCE_ITEMS=8`, `CITED_RAG_CONTEXT_TOKEN_BUDGET=1500`
- no-answer: `CITED_RAG_MIN_RERANK_SCORE=0` until a larger set sets a baseline

Do not optimize Recall@K in isolation: a higher K can still produce a worse cited answer if rerank buries the page or generation invents IDs.
