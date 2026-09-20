# UI-04 — Glass Box

## Trace JSON is a product contract

Log spans are useful for operators, but a process-global list is not safe to
return to a browser: concurrent requests can mix tenants and stages. The query
route starts a `ContextVar`-backed buffer, snapshots it into the HTTP 200 body,
and clears it in `finally`. Each response always contains the six ordered
product stages; stages not reached by an honest no-answer path are marked
`skipped` rather than omitted.

Evidence cards expose application-owned `E1..En` identities and page
provenance. PDF text remains untrusted data and is rendered as React text
nodes, never HTML. The trace caps both evidence count and text length, marking
truncated text explicitly. Operational failures still return the existing 503
shape with no trace; an abstention remains a successful 200 response with its
trace and reason.
