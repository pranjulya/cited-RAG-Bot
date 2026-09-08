# Phase 09 — Hybrid Retrieval and RRF

## Why not average dense and sparse scores?

Dense cosine and sparse lexical scores live on different scales. A 0.82 cosine is not comparable to a 4.1 sparse dot product. Averaging or min-max mixing pretends they are the same unit and lets whichever retriever shouts louder dominate. Reciprocal Rank Fusion ignores raw scores and adds `1 / (k + rank)` from each list.

## What is RRF?

For each chunk, sum `1 / (k + rank_r)` over the rank lists that contain it. `k` (`CITED_RAG_RRF_K`, default 60) dampens the first ranks so rank 1 is not an order of magnitude above rank 2. Overlap is rewarded because a chunk in both lists gets two terms. Ties break on `chunk_id` so the fused order is deterministic.

## What problem does hybrid retrieval solve?

Dense search finds paraphrases. Sparse search finds identifiers, numbers, and rare tokens. Hybrid recall is the union, with overlap boosted. Production still runs both retrievers; a timeout or store error is `DENSE_RETRIEVAL_ERROR` / `SPARSE_RETRIEVAL_ERROR`. An empty hit list is not an error: fuse the surviving list. Dense-only or sparse-only runs belong to `EvaluationRunConfig`, not a production fallback.

## Why measure hybrid against baselines?

If hybrid never beats dense-only or sparse-only on the golden set, fusion is ceremony. Evaluation (Phase 19) compares those ablations with the same `EvaluationRunConfig` flags used here, without changing the online fail-closed policy.
