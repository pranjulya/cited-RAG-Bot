# UI-06 — Fail-Closed Studio

The console keeps product outcomes distinct: `INSUFFICIENT_EVIDENCE` is a
successful 200 response, while a 503 is an operational outage and a 401
returns to the API-key gate. Query validation failures and missing sources get
their own copy instead of being collapsed into a generic error.

Document deletion follows the API's tombstone contract. The UI confirms the
destructive action, calls `DELETE`, then polls the existing document endpoint
until it returns 404 before removing the row. This keeps the browser aligned
with authoritative server state and avoids pretending that a `DELETING`
response is already gone.

Failed ingestion keeps its server-owned `failure_code` visible as a link, so a
demo can jump directly to the failure state without inventing a client-side
reason.
