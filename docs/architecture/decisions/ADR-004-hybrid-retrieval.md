# ADR-004 — Hybrid Retrieval and Fusion

**Status:** Proposed  
**Decision:** Retrieve dense and sparse candidates independently, then combine them using Reciprocal Rank Fusion (RRF) for V1.

## Context

Dense search captures semantic similarity while sparse search is stronger for exact names, identifiers, numbers, uncommon terms, and exact phrases. Their raw scores are not directly comparable.

## Decision

The retrieval pipeline will:

1. retrieve configurable top-K dense candidates;
2. retrieve configurable top-K sparse candidates;
3. deduplicate by stable chunk_id;
4. combine ranked lists with RRF;
5. return a configurable candidate set to the reranker.

Fusion lives behind a `FusionStrategy` interface.

## Why RRF

RRF operates on rank positions rather than assuming dense and sparse score scales are comparable. It is deterministic, easy to explain, and provides a strong V1 baseline.

## Alternatives Considered

- weighted normalized score fusion;
- learned fusion;
- dense-only retrieval;
- sparse-only retrieval.

Weighted or learned fusion should only replace the baseline if evaluation demonstrates meaningful improvement.

## Failure Behavior To Decide

Architecture review must lock whether one retriever failing causes:

- fail-closed query behavior; or
- explicit degraded mode using the surviving retriever.

Silent degradation is not allowed.

## Validation Required

Evaluation must measure dense-only, sparse-only, and hybrid Recall@K/MRR/nDCG where appropriate.