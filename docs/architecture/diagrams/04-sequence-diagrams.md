# 04 — Runtime Sequence Diagrams

## A. Upload and Asynchronous Ingestion

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Store as Object Storage
    participant PG as PostgreSQL
    participant Queue as Redis Queue
    participant Worker
    participant Parser
    participant Embed as Embedding Provider
    participant QD as Qdrant

    Client->>API: POST PDF
    API->>API: Validate type / size / request
    API->>Store: Persist original PDF
    API->>PG: Create document/version = UPLOADED
    API->>Queue: Enqueue ingestion job
    API->>PG: Set QUEUED
    API-->>Client: 202 Accepted + QUEUED

    Queue->>Worker: Deliver ingestion job
    Worker->>PG: Set PROCESSING
    Worker->>Store: Load source PDF
    Worker->>Parser: Parse preserving page boundaries
    Parser-->>Worker: PageContent[]
    Worker->>Worker: Normalize + provenance-aware chunking
    Worker->>PG: Persist page/chunk provenance
    Worker->>Embed: Create dense/sparse representations
    Embed-->>Worker: Retrieval representations
    Worker->>QD: Upsert named dense/sparse vectors on chunk UUID
    Worker->>Worker: Verify completeness
    Worker->>PG: Set READY + active_version_id
```

## B. Online Query

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant PG as PostgreSQL
    participant Dense
    participant Sparse
    participant Fusion
    participant Reranker
    participant Context
    participant LLM
    participant Citation

    Client->>API: Query(collection_id, question)
    API->>PG: Authorize collection + find READY documents

    par Dense retrieval
        API->>Dense: retrieve(question, collection)
        Dense-->>API: candidates
    and Sparse retrieval
        API->>Sparse: retrieve(question, collection)
        Sparse-->>API: candidates
    end

    API->>Fusion: RRF(dense, sparse)
    Fusion-->>API: fused candidates
    API->>Reranker: rerank(question, candidates)
    Reranker-->>API: ranked evidence
    API->>Context: build evidence package
    Context-->>API: approved evidence + evidence IDs

    alt Evidence insufficient
        API-->>Client: INSUFFICIENT_EVIDENCE
    else Evidence sufficient
        API->>LLM: Generate only from supplied evidence
        LLM-->>API: answer + evidence-ID citations
        API->>Citation: Validate citation identities
        Citation->>PG: Resolve authoritative provenance
        Citation-->>API: validated page citations
        API-->>Client: Answer + citations
    end
```

## C. Citation Validation

```mermaid
sequenceDiagram
    participant Generator
    participant Validator
    participant EvidenceSet
    participant PG as PostgreSQL
    participant API

    Generator-->>Validator: answer + cited evidence IDs
    Validator->>EvidenceSet: Was each evidence ID approved for this request?

    alt Evidence ID not approved
        Validator-->>API: Citation validation failure
    else Evidence ID approved
        Validator->>PG: Resolve document/version/page/chunk
        PG-->>Validator: authoritative provenance
        Validator->>Validator: verify collection + mapping
        Validator-->>API: validated external citations
    end
```

## Design Rule

Provider retries, retrieval degradation, generation repair, and ingestion retry behavior must be made explicit in LLD. These diagrams describe the successful logical path and the major controlled branches, not hidden retry loops.
