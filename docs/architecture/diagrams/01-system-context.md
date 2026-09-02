# 01 — System Context Diagram

## Purpose

Shows the major users, external providers, runtime services, and infrastructure boundaries around Cited RAG Bot.

```mermaid
flowchart LR
    USER[User / Client Application]

    subgraph RAG[Cited RAG Bot]
        API[Cited RAG API]
        WORKER[Ingestion Worker]
    end

    OBJ[(PDF Object Storage)]
    PG[(PostgreSQL)]
    REDIS[(Redis / Queue)]
    QD[(Qdrant)]

    EMB[Embedding Provider]
    RR[Reranker Provider]
    LLM[Generation Provider]
    OBS[Logs / Metrics / Traces]

    USER -->|Upload PDFs / Query collections| API

    API --> PG
    API --> OBJ
    API --> REDIS
    API --> QD
    API --> RR
    API --> LLM

    REDIS --> WORKER
    WORKER --> OBJ
    WORKER --> PG
    WORKER --> EMB
    WORKER --> QD

    API --> OBS
    WORKER --> OBS
```

## Boundary Notes

- The API owns synchronous client interactions.
- The worker owns long-running ingestion.
- PostgreSQL owns durable application metadata and provenance.
- Qdrant owns searchable dense/sparse retrieval representations.
- Redis coordinates asynchronous work and must not become the authoritative metadata store.
- Object storage retains source PDFs.
- Embedding, reranking, and generation providers remain replaceable behind adapters.
