# Phase 16 — Document Deletion and Index Consistency

## Why tombstone before cleanup?

PostgreSQL `DELETING` plus `deleted_at` removes the version from the READY/active filter immediately. Qdrant and object storage are derived stores and may fail independently. If we deleted blobs first and crashed, the document could still be searchable. Tombstone first: queries stop; cleanup can retry.

## Why deletion is not one transaction

Postgres, Qdrant, and local/S3 storage do not share a commit. The compensating action is a retryable `cleanup_deleted_document` job that deletes points by `document_version_id`, removes the source PDF, then marks `DELETED`. Repeating the job is safe.

## Idempotency and orphans

Deleting points for a version that is already gone is a no-op. Reconciliation is: every Qdrant point’s version must still exist as a non-deleted Postgres version. Orphans are leftover points after a crash; the cleanup job is the fix.
