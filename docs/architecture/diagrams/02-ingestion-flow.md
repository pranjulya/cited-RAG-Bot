# 02 — PDF Ingestion Architecture

## Purpose

Shows how an uploaded PDF becomes a collection of searchable, provenance-aware evidence records.

```mermaid
flowchart TD
    CLIENT[Client]
    API[Document API]
    VALIDATE[Upload Validation]
    STORE[(Object Storage)]
    PG[(PostgreSQL)]
    QUEUE[(Redis Queue)]
    WORKER[Ingestion Worker]
    PARSER[Page-Aware Parser]
    NORMALIZE[Content Normalizer]
    CHUNK[Provenance-Aware Chunker]
    EMBED[Embedding / Sparse Representation]
    INDEX[Indexing Coordinator]
    QD[(Qdrant)]

    CLIENT -->|PDF Upload| API
    API --> VALIDATE
    VALIDATE -->|Valid PDF| STORE
    VALIDATE -->|Create document/version| PG
    VALIDATE -->|Enqueue ingestion| QUEUE

    QUEUE --> WORKER
    WORKER -->|Load source PDF| STORE
    WORKER -->|Set PROCESSING| PG
    WORKER --> PARSER
    PARSER --> NORMALIZE
    NORMALIZE --> CHUNK
    CHUNK -->|Persist pages/chunks| PG
    CHUNK --> EMBED
    EMBED --> INDEX
    INDEX --> QD
    INDEX -->|Verify dense+sparse completeness| READY[Set document version READY]
    READY --> PG

    PARSER -. failure .-> FAILED[Set FAILED + classified reason]
    EMBED -. failure .-> FAILED
    INDEX -. failure .-> FAILED
    FAILED --> PG
```

## Ingestion Contract

A document may become `READY` only after all mandatory V1 retrieval artifacts are successfully created.

The expected lifecycle is:

```text
UPLOADED
   ↓
QUEUED
   ↓
PROCESSING
   ├──→ READY
   └──→ FAILED
READY → DELETING → DELETED
```

`READY` requires PostgreSQL provenance plus dense and sparse named vectors on each chunk UUID (ADR-011).

## Provenance Requirement

Every chunk produced by ingestion must retain at minimum:

```text
collection_id
document_id
document_version
page_number / explicit page range
chunk_id
chunk_order
normalized_text
```

## Failure Principle

Partial indexing is not success. Retry/recovery must be idempotent at document-version level and will be specified in the LLD.
