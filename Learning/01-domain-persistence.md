# Phase 01 — Domain Model and Persistence

## Why is PostgreSQL authoritative while search indexes are derived?

Collections, versions, pages, and chunks are the product’s audit trail. A retrieval index can be rebuilt, dropped, or filtered incorrectly. If Qdrant were the only copy of “chunk 12 is page 17 of version 3,” a bad upsert or a missed delete would invent or lose citations. PostgreSQL stores that chain with foreign keys. Qdrant later holds vectors whose point id is the chunk UUID already in PostgreSQL. READY is not set until both exist; the metadata row is still the source of truth for identity, ownership, and lifecycle.

## Repository pattern tradeoffs

Domain entities are frozen dataclasses. SQLAlchemy rows live in `adapters/persistence/postgres`. Ports in `cited_rag.ports.repositories` describe add/get/transition without leaking sessions.

Benefits: unit tests can exercise lifecycle policy with no database; later SQLite-in-memory experiments cannot quietly become the production store; application services depend on `UnitOfWork`, not on `AsyncSession`.

Costs: mapping code (`mapping.py`) must stay in sync with the migration; a second representation can drift if a column is added in only one place. Phase 01 accepts that cost because provenance rules must not be buried in ORM events.

## Why transaction boundaries matter for RAG provenance

A document version, its pages, and its chunks are one durable fact. If the version commits and the chunks roll back, retrieval can point at a UUID that has no text, or generation can cite a page that was never stored. The unit of work commits on success and rolls back on any exception so a failed ingest step cannot leave a half-written chain. Duplicate primary keys and the per-collection content-hash unique index fail the same way: the transaction does not keep the partial insert.

Lifecycle updates are optimistic: `UPDATE … WHERE id = ? AND ingestion_status = <expected>`. A stale worker cannot mark READY over a version that already moved to FAILED.

## Lifecycle (ADR-011)

```text
UPLOADED → QUEUED → PROCESSING → READY
                              ↘ FAILED
FAILED → QUEUED
READY → DELETING → DELETED
```

Invalid jumps (for example `UPLOADED → READY`) are rejected in domain policy before SQL runs.

## Content-hash uniqueness

The same PDF may exist in two collections. Inside one collection, a non-deleted version’s `content_hash` is unique (`ingestion_status <> 'DELETED'`). That is a partial unique index on `(collection_id, content_hash)` on `document_versions`, not a global hash key.

## Chunk identity

Chunk ids are UUIDv5 from version id, page range, chunk order, and content hash. That UUID is the future Qdrant point id. PostgreSQL stores it first.

## What this phase does not do

No upload API, no object storage, no worker, no Qdrant, no evaluation tables. `/ready` stays `not_configured` until a later phase checks real dependencies.
