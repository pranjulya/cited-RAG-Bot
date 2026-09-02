# ADR-010 — Evaluation Gates

**Status:** Accepted  
**Decision:** Treat retrieval, reranking, answer groundedness, citation quality, and no-answer behavior as independent evaluation dimensions. Maintain a versioned golden dataset and use evaluation results as release gates after baseline thresholds are established.

## Context

A RAG system can produce a plausible answer while retrieval is wrong, citations are irrelevant, or unsupported claims are present. End-to-end subjective testing cannot diagnose which stage failed.

## Decision

The evaluation harness must expose and measure at least:

### Retrieval
- Recall@K
- MRR
- nDCG where useful
- dense-only vs sparse-only vs hybrid comparisons

### Reranking
- before/after ranking quality
- latency impact

### Answer
- relevance
- groundedness/faithfulness
- unsupported-claim rate

### Citations
- validity
- correctness
- completeness

### No-answer
- appropriate refusal when evidence is absent
- false-answer rate on unanswerable questions

The golden dataset must include factual, semantic, exact-keyword, multi-page, multi-document, no-answer, and adversarial cases.

## Consequences

- Architecture must retain intermediate retrieval/rerank artifacts for evaluation/debugging.
- Configuration changes to chunking, embeddings, fusion, reranking, or prompts require benchmark comparison.
- Thresholds are not invented before a baseline is measured.

## Validation Required

Dataset format and metric families are in `docs/evaluation/evaluation-strategy.md`. Numeric release thresholds are still not invented before a baseline. Ablations use `EvaluationRunConfig`; they must not reuse a production degraded-retrieval flag (ADR-011).