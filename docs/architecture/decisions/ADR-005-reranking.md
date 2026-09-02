# ADR-005 — Reranking

**Status:** Proposed  
**Decision:** Add a replaceable reranking stage after hybrid retrieval and before context construction.

## Context

Hybrid retrieval optimizes candidate recall. The generation model should receive a smaller, higher-quality evidence set. Reranking must therefore be evaluated as a separate stage rather than assumed to help.

## Decision

Introduce a `Reranker` abstraction that accepts the user query and fused candidates and returns an ordered list with rerank scores/metadata.

The default implementation should use a cross-encoder-style reranker appropriate for the deployment environment. The exact model/provider remains configuration rather than domain logic.

## Pipeline

```text
Dense + Sparse Retrieval
        ↓
RRF Candidate Set
        ↓
Reranker
        ↓
Top-N Evidence
        ↓
Context Builder
```

## Consequences

- Reranker latency is measured independently.
- Reranking can be disabled for baseline evaluation.
- Hosted and local rerankers can be swapped through adapters.
- Context selection must use the reranked order, not raw retrieval scores.

## Failure Behavior To Decide

Architecture review must choose whether reranker failure results in controlled fallback to fused ranking or a failed query. Any fallback must be observable.

## Validation Required

The evaluation harness must compare retrieval metrics before and after reranking and quantify the latency/quality trade-off.