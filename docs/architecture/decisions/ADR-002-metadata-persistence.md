# ADR-002 — Durable Metadata Persistence

**Status:** Accepted  
**Decision:** Use PostgreSQL as the durable system of record for application metadata, provenance, ingestion state, document versions, and query audit metadata.

## Context

The system must preserve auditable provenance independently of the retrieval engine. Search indexes are optimized for retrieval and may be rebuilt, deleted, or migrated.

## Decision

PostgreSQL owns durable records for:

- collections
- documents
- document versions
- pages
- chunks and provenance metadata
- ingestion jobs/status
- deletion state
- query/citation audit metadata where retained
- evaluation dataset metadata where appropriate

Retrieval indexes are derived artifacts and must be reconstructable.

## Consequences

- Search infrastructure cannot become the only provenance source.
- Deletion workflows must coordinate PostgreSQL and retrieval indexes.
- Schema migrations use Alembic.
- Repository/service boundaries hide ORM details from domain logic.

## Alternatives Considered

- Retrieval database as the only persistence layer: rejected because it weakens auditability and lifecycle consistency.
- Document database as primary metadata store: possible, but relational constraints fit collections, versions, ingestion state, and provenance well.

## Validation Required

LLD must define transaction boundaries and recovery behavior for partial indexing/deletion failures.