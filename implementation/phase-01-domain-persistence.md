# Phase 01 — Core Domain Model and Persistence Foundation

**Status:** NOT_STARTED

## Goal
Define durable domain entities and PostgreSQL persistence without yet implementing upload or retrieval behavior.

## Prerequisites
Phase 00 COMPLETE.

## Architecture References
`docs/architecture/LLD.md`, ADR-002, `Implementation.md`.

## Concepts to Learn
Domain modeling, repository pattern, SQLAlchemy session boundaries, Alembic migrations, optimistic lifecycle transitions, UUID/ULID identifiers, transactional consistency.

## Planned Deliverables
Domain models for collection, document, document version, page, chunk, ingestion job, query/audit metadata; SQLAlchemy mappings; repository interfaces/adapters; initial migrations.

## Implementation Tasks
1. Define enums and immutable identifiers.
2. Define domain entities independent of SQLAlchemy where practical.
3. Define repository ports.
4. Implement PostgreSQL adapters.
5. Create Alembic migration for core tables and indexes.
6. Enforce relationships and uniqueness rules around document/version/chunk provenance.
7. Add transaction helpers and test fixtures.

## Required Tests
- create/read collection;
- document belongs to collection;
- document version lifecycle persistence;
- page/chunk provenance survives round trip;
- duplicate identifiers rejected;
- rollback leaves no partial state.

## Failure Scenarios
DB unavailable, failed migration, uniqueness conflict, invalid lifecycle transition, transaction rollback.

## Acceptance Criteria
PostgreSQL can recreate the complete durable metadata chain `collection → document → version → page → chunk` and migrations are reproducible.

## Definition of Done
Persistence contracts, migrations, integration tests, review, and Learning notes completed.

## What I Must Be Able to Explain
Why PostgreSQL is authoritative while search indexes are derived? Repository pattern tradeoffs? Why transaction boundaries matter for RAG provenance?