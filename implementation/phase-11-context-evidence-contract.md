# Phase 11 — Context Builder and Evidence Contract

**Status:** NOT_STARTED

## Goal
Build model-ready context from approved reranked evidence while enforcing token/evidence budgets and assigning request-scoped evidence IDs.

## Prerequisites
Phase 10 COMPLETE.

## References
ADR-006, HLD Context Builder, LLD evidence contract, data-provenance diagram.

## Concepts to Learn
Context windows, token budgeting, evidence packing, deduplication, request-scoped identifiers, trust boundaries.

## Planned Deliverables
Context builder service, evidence package model, token-budget calculator, deterministic `E1..En` assignment.

## Tasks
1. Accept only reranked approved candidates.
2. Resolve authoritative chunk/page provenance.
3. Deduplicate/merge only with explicit rules.
4. Enforce evidence count and token budget.
5. Assign `E1`, `E2`, ... per request.
6. Produce mapping from evidence ID to authoritative chunk/document/page **server-side**.
7. Model-facing context is evidence ID + chunk text only. Do not send document_id, chunk_id, or page numbers to the model.

## Tests
Budget trimming, stable evidence order, duplicate handling, mapping integrity, empty evidence, oversized chunk.

## Failure Scenarios
Missing authoritative chunk, budget exceeded, no admissible evidence, mapping collision.

## Acceptance Criteria
Generation receives only approved evidence with application-owned request-scoped IDs.

## Definition of Done
Context/evidence tests, review, docs, Learning notes complete.

## What I Must Be Able to Explain
Why use E1/E2 rather than ask the LLM to output page numbers directly? What is the context builder trust boundary? Why does token budgeting affect answer quality and cost?