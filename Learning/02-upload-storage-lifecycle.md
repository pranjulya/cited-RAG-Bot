# Phase 02 — PDF Upload, Storage, and Lifecycle

## Why keep original PDFs?

The parser, chunker, and indexes are derived. A parser upgrade, a failed ingest, or a citation check needs the same bytes that were uploaded. PostgreSQL stores metadata and provenance; object storage keeps the immutable source at `collections/{collection_id}/documents/{document_id}/versions/{version_id}/source.pdf`.

## Why hash uploads?

SHA-256 of the file is the collection-scoped identity of those bytes. The same PDF in two collections is two documents. The same bytes in one collection return the existing document/version (idempotent). A `FAILED` version is not a second document; retry is `FAILED → QUEUED` in Phase 03.

## Why `UPLOADED` is not searchable

`READY` means pages/chunks exist in PostgreSQL **and** dense+sparse vectors exist in Qdrant. Upload only stores the PDF and a version row. Phase 02 persists `UPLOADED` internally because enqueue does not exist yet. The public `202` and GET status is `QUEUED` so clients never treat `UPLOADED` as the product contract.

## Object store vs database transactions

`put` is not in the same transaction as the metadata insert. The service writes the object first, then the rows. If the database write fails, it deletes the object (compensation). If the object write fails, no rows are created. Duplicate-hash races after a successful `put` also delete the extra object and return the existing row.

## Auth and collection scope

`Authorization: Bearer <api_key>` is required on `/v1/*`. `/health` and `/ready` stay open. Collection `owner_id` is the API principal. Missing and unauthorized documents both return `404`.
