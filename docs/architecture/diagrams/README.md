# Step 4 — Architecture Diagrams

**Project:** Cited RAG Bot  
**Status:** Accepted for implementation (ADR-011 freeze)  
**Version:** 1.1

## Purpose

This folder is the visual architecture reference for Project 04. The diagrams are derived from the PRD, accepted ADRs (including ADR-011), and HLD.

The diagrams intentionally separate different architectural views instead of forcing the entire system into one oversized diagram.

## Diagram Set

| File | View | Primary Question |
|---|---|---|
| `01-system-context.md` | System context | What systems and actors interact with Cited RAG Bot? |
| `02-ingestion-flow.md` | PDF ingestion | How does a PDF become searchable evidence? |
| `03-query-retrieval-flow.md` | Online RAG query | How does a user question become a cited answer? |
| `04-sequence-diagrams.md` | Runtime sequences | What happens step by step during upload, ingestion, query, and citation validation? |
| `05-deployment-runtime.md` | Deployment/runtime | Which runtime components and infrastructure are deployed? |
| `06-data-provenance.md` | Citation provenance | How is provenance preserved from PDF page to final citation? |

## Architecture Invariants Shown By These Diagrams

1. PDF source content is never queried directly by the LLM.
2. PDF pages are converted into provenance-aware chunks before indexing.
3. PostgreSQL remains the authoritative metadata/provenance store.
4. Qdrant is a derived retrieval index, not the sole source of citation truth.
5. Ingestion is asynchronous.
6. Dense and sparse retrieval are independent strategies before fusion.
7. Reranking happens after initial candidate retrieval.
8. Only approved evidence reaches the generation model.
9. Citation identities are generated and validated by the application.
10. The system may return `INSUFFICIENT_EVIDENCE` instead of generating an unsupported answer.

## Review Rule

If a future HLD, LLD, ADR, or implementation phase contradicts these diagrams, the contradiction must be resolved explicitly. Do not silently update code while leaving the architecture documents inconsistent.
