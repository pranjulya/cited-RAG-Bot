# 03 — Query and Retrieval Architecture

## Purpose

Shows how a user question becomes a grounded answer with validated PDF page citations.

```mermaid
flowchart TD
    CLIENT[Client]
    API[Query API]
    ACCESS[Collection Access + READY Document Check]
    QPROC[Query Processing]

    DENSE[Dense Retriever]
    SPARSE[Sparse Retriever]
    QD[(Qdrant)]

    FUSION[Reciprocal Rank Fusion]
    RERANK[Reranker]
    EVIDENCE[Evidence Selection / Context Builder]
    POLICY{Sufficient Evidence?}
    LLM[Grounded Generation]
    CITE[Citation Validator]
    PG[(PostgreSQL Provenance)]

    ANSWER[Answer + Page Citations]
    NOANSWER[INSUFFICIENT_EVIDENCE]
    ERROR[Controlled Failure]

    CLIENT --> API
    API --> ACCESS
    ACCESS --> QPROC

    QPROC --> DENSE
    QPROC --> SPARSE
    DENSE --> QD
    SPARSE --> QD

    DENSE --> FUSION
    SPARSE --> FUSION
    FUSION --> RERANK
    RERANK --> EVIDENCE
    EVIDENCE --> POLICY

    POLICY -->|No| NOANSWER
    POLICY -->|Yes| LLM

    LLM --> CITE
    CITE --> PG
    CITE -->|Valid| ANSWER
    CITE -->|Invalid citation identity / mapping| ERROR

    ANSWER --> CLIENT
    NOANSWER --> CLIENT
    ERROR --> CLIENT
```

## Query Pipeline

```text
Question
   ↓
Collection-scoped validation + active READY version filter
   ↓
Dense retrieval + Sparse retrieval
(both filter collection_id and active READY version ids)
   ↓
RRF fusion
   ↓
Reranking
   ↓
Evidence selection
   ↓
Evidence sufficiency decision
   ↓
Grounded generation
   ↓
Deterministic citation validation
   ↓
Answer + document/page citations
```

## Critical Trust Boundary

The LLM receives only the evidence selected by the context builder. It does not receive direct access to Qdrant, PostgreSQL, or source PDFs.

The model may reference only application-generated evidence IDs. The application maps those IDs back to authoritative document/page/chunk provenance.

## No-Answer Principle

No-answer is an expected outcome, not an exception. If the evidence cannot support a trustworthy response, the system returns `INSUFFICIENT_EVIDENCE` rather than filling gaps from model knowledge.
