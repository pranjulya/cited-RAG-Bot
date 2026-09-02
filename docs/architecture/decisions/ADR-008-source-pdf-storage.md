# ADR-008 — Source PDF Storage

**Status:** Accepted  
**Decision:** Retain original uploaded PDFs through an object-storage abstraction. Use local filesystem storage for development and S3-compatible storage for production deployments.

## Context

The system needs the original document for auditability, reprocessing, parser upgrades, reindexing, citation verification, and document-version lifecycle operations.

## Decision

Introduce an `ObjectStorage` abstraction (`DocumentStorage` in earlier drafts refers to the same port). Application/database records store durable object references rather than embedding file bytes in PostgreSQL.

## Consequences

- Reindexing does not require the user to upload the PDF again.
- Document deletion must remove/invalidate both source objects and derived search artifacts.
- Storage retention and privacy policies must be explicit.
- Local development remains simple while production architecture remains cloud-compatible.

## Alternatives Considered

- Store PDFs directly in PostgreSQL: rejected for V1 because it couples large binary lifecycle to relational metadata.
- Delete PDFs immediately after indexing: rejected because it harms reproducibility and reprocessing.

## Validation Required

Key layout, retention until document/version deletion, and local-vs-S3 adapters are specified in LLD §18 and ADR-011. TLS and encryption-at-rest for production object storage are Phase 18 hardening requirements.