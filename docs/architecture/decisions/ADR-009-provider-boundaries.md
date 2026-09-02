# ADR-009 — Model and Provider Boundaries

**Status:** Proposed  
**Decision:** Embedding, reranking, and generation capabilities must be accessed through explicit provider interfaces/adapters.

## Context

The project should teach architecture, not lock itself to one SDK. Providers, models, pricing, limits, and APIs change independently from RAG domain logic.

## Decision

Define separate contracts such as:

- `EmbeddingProvider`
- `Reranker`
- `GenerationProvider`

Provider-specific request/response types stay inside adapters. Core services consume domain models.

Configuration selects the active implementation and model.

## Consequences

- Tests can use deterministic fakes.
- Provider changes do not rewrite retrieval/generation orchestration.
- Model-specific limits are handled through configuration/capability metadata.
- Observability can normalize latency/token/error metrics across providers.

## Anti-Pattern

Do not scatter direct provider SDK calls across API routes, retrieval services, or domain logic.

## Validation Required

LLD must define normalized domain contracts, error mapping, timeout ownership, and retry boundaries.