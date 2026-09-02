# Phase 05 — Provenance-Aware Chunking

**Status:** NOT_STARTED

## Goal
Convert parsed page content into configurable retrieval chunks without losing source identity.

## Prerequisites
Phase 04 COMPLETE.

## References
PRD FR-05, HLD chunker, LLD chunk contract, evaluation strategy.

## Concepts to Learn
Chunk size/overlap, semantic boundaries, page-boundary tradeoffs, token-aware splitting, deterministic chunk IDs.

## Planned Deliverables
Chunker port, configurable implementation, chunk metadata builder, deterministic ordering/identity.

## Tasks
1. Define `Chunk` contract with collection/document/version/page/chunk/order/text.
2. Implement configurable token/character aware splitting.
3. Preserve one page or explicit page range for every chunk.
4. Generate deterministic chunk IDs from stable provenance inputs.
5. Persist chunk metadata/text.
6. Record chunking configuration for reproducibility.

## Tests
Single-page, multi-page, very short page, long page, overlap behavior, deterministic IDs, no provenance loss.

## Failure Scenarios
Empty pages, giant unbroken text, page-boundary ambiguity, duplicate chunks.

## Acceptance Criteria
Every chunk is reproducible, ordered, and traceable to authoritative source pages.

## Definition of Done
Chunking tests, review, docs, Learning notes complete.

## What I Must Be Able to Explain
Why chunking affects recall? Why fixed-size chunks are not universally optimal? Why chunk configuration belongs in evaluation metadata?