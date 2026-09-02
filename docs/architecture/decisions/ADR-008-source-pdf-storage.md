# ADR-008 — Source PDF Storage

**Status:** Proposed  
**Decision:** Retain original uploaded PDFs through an object-storage abstraction. Use local filesystem storage for development and S3-compatible storage for production deployments.

## Context

The system needs the original document for auditability, reprocessing, parser upgrades, reindexing, citation verification, and document-version lifecycle operations.

## Decision

Introduce a `DocumentStorage` abstraction. Application/database records store durable object references rather than embedding file bytes in PostgreSQL.

## Consequences

- Reindexing does not require the user to upload the PDF again.
- Document deletion must remove/invalidate both source objects and derived search artifacts.
- Storage retention and privacy policies must be explicit.
- Local development remains simple while production architecture remains cloud-compatible.

## Alternatives Considered

- Store PDFs directly in PostgreSQL: rejected for V1 because it couples large binary lifecycle to relational metadata.
- Delete PDFs immediately after indexing: rejected because it harms reproducibility and reprocessing.

## Validation Required

Security design must define encryption, access permissions, file naming/key strategy, retention, and secure deletion expectations.