# UI-04 — Glass Box

**Status:** NOT_STARTED

## Goal
The same query, with visible stages, evidence `E1..En`, timings, and correlation id. This is the resume/technical demo.

## Prerequisites
UI-03 COMPLETE.

## References
`observability/tracing.py`, `QUERY_STAGES`, evidence package, ADR-006 / ADR-012.

## Concepts to Learn
Trace as product data vs logs. Untrusted evidence rendering. Correlation id as support handle.

## Planned Deliverables
Query trace payload: ordered stages (`request`, `fusion`, `rerank`, `context_build`, `generation`, `citation_validate`) with duration_ms and status; evidence list `{id, text, document_name, page_start, page_end}`; `correlation_id`. UI: timeline + evidence cards. Click citation chip highlights matching E-ID.

## Tasks
1. Backend: add a `trace` object on the existing query JSON (same request). Do not add `GET /v1/queries/{id}` in this phase. Do not log evidence text by default.
2. Truncate evidence text in API if huge.
3. UI renders text as text (no HTML). Stage failure shows which stage failed for 503s when the API can say so.
4. Learning note.

## Tests
Trace present on ANSWERED and on INSUFFICIENT. Evidence ids match citations. UI does not `dangerouslySetInnerHTML`. Cross-collection GET query 404.

## Failure Scenarios
Missing trace on old clients — UI still shows answer (trace optional at first, required for this phase’s acceptance).

## Acceptance Criteria
A reviewer can point at E1, the fused/rerank/generate/validate steps, and the correlation id for one request.

## Definition of Done
Trace API + inspector UI, tests, Demo, Learning.

## Demo
1. Repeat “How much leave?”
2. Open Glass box: walk retrieve → rerank → generate → validate.
3. Open E1 card; match citation page.
4. Copy correlation id; show it in `docker compose logs api | grep <id>` (redacted question).

## What I Must Be Able to Explain
Why traces are application data, not an APM vendor. Why evidence is untrusted. Why correlation is better than “check the logs around 3pm”.
