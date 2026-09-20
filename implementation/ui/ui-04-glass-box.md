# UI-04 — Glass Box

**Status:** TESTED

## Goal
The same HTTP 200 query response, with a **request-scoped** `trace` so the console can show stages, evidence `E1..En`, timings, and correlation id.

## Prerequisites
UI-03 COMPLETE.

## References
`src/cited_rag/observability/tracing.py` (today: process-global `traces = TraceBuffer()`), `src/cited_rag/observability/stages.py`, `src/cited_rag/application/query.py` `span("query.*")` calls, evidence package, ADR-006 / ADR-012.

`QUERY_STAGES` in `stages.py` is **not** the product catalog. It currently lists `query.access_check`, `query.dense_retrieval`, and `query.sparse_retrieval`, which `answer_question` never spans. UI-04 must update `QUERY_STAGES` to match the catalog below (membership tests follow the catalog).

## Concepts to Learn
Trace as product JSON vs log lines. ContextVar isolation vs a process-global list. Untrusted evidence rendering.

## Product catalog (locked)

Ordered stage names on every HTTP **200** query response:

```text
query.request
query.fusion
query.rerank
query.context_build
query.generation
query.citation_validate
```

These are the `span()` names already used in `answer_question`, plus skipped placeholders (see below). Do not emit `query.access_check` / `query.dense_retrieval` / `query.sparse_retrieval` unless a later ADR adds those spans.

## Response schema (locked)

`QueryResponse.trace` is **required** on HTTP 200 (ANSWERED and INSUFFICIENT_EVIDENCE). HTTP 401/404/413/422/503 stay `{detail: ...}` with **no** `trace`.

```json
{
  "request_id": "uuid",
  "status": "ANSWERED",
  "answer": "...",
  "citations": [],
  "reason": null,
  "trace": {
    "correlation_id": "uuid-or-header",
    "stages": [
      {"name": "query.request", "duration_ms": 12, "status": "ok"}
    ],
    "evidence": [
      {
        "id": "E1",
        "document_id": "uuid",
        "document_version_id": "uuid",
        "document_name": "policy.pdf",
        "page_start": 1,
        "page_end": 1,
        "text": "...",
        "truncated": false
      }
    ]
  }
}
```

- `stages[].name`: one of the catalog strings, in catalog order, **exactly six entries**.
- `stages[].status`: `ok` | `error` | `skipped`.
- `stages[].duration_ms`: integer ≥ 0; `0` when `skipped`.
- `evidence[].id`: application evidence id (`E1`…); never `chunk_id`.
- `evidence[].text`: untrusted PDF text; UTF-8; truncated to `CITED_RAG_TRACE_EVIDENCE_CHARS` (default **2000**) with `truncated: true` if cut. Cap list length at `settings.max_evidence_items`.
- `correlation_id`: same value as `X-Correlation-ID` on that response.

## Request isolation (locked)

Today `cited_rag.observability.tracing.traces` is a **process-global** list. That is not a product trace.

UI-04 replaces the query path with a **ContextVar** buffer:

- `start_trace()` / `take_trace()` (names flexible) bound to the current task.
- `span()` appends only to the current context.
- The query route snapshots the buffer into `QueryResponse.trace` and clears it in `finally`.
- Concurrent `answer_question` calls must not see each other’s spans.

Keep log lines as they are; the product JSON is the snapshot, not `traces.spans` after the fact.

## Skipped stages (locked)

Always return six catalog rows.

| Early exit | `ok` | `skipped` |
|---|---|---|
| No READY versions (`NO_READY_DOCUMENTS`) inside `query.request` | `query.request` | fusion, rerank, context_build, generation, citation_validate |
| `decide_before_generation` (weak/empty evidence) | request, fusion, rerank, context_build | generation, citation_validate |
| `decide_after_generation` (model abstention) | request through generation **and** citation_validate (validation still runs today) | none extra |
| ANSWERED | all six `ok` | none |

If a spanned stage raises, the query route today becomes HTTP 503 with no body trace. **Leave that.** Glass-box 503 UX is UI-06.

## Truncation (locked)

- Evidence text: max `CITED_RAG_TRACE_EVIDENCE_CHARS` (default 2000) per item.
- Evidence count: `min(len(records), settings.max_evidence_items)`.
- Do not put raw PDF text in logs when attaching trace (`log_sensitive_content` still gates query logs).

## Planned Deliverables
ContextVar trace; `trace` on QueryResponse; `QUERY_STAGES` aligned to the catalog; glass-box UI (timeline + evidence cards). Citation chip highlights matching `id`.

## Tasks
1. ContextVar buffer; stop using the global list for query responses.
2. Assemble six catalog stages + evidence from the evidence package (empty list when skipped before context).
3. UI: text nodes only (no `innerHTML`).
4. Learning note.

## Tests
- ANSWERED: six `ok` stages; evidence ids match citations.
- `NO_READY_DOCUMENTS`: request `ok`, other five `skipped`, evidence `[]`.
- Weak evidence before generation: generation + citation_validate `skipped`.
- Abstention after generation: citation_validate present (`ok`).
- Evidence longer than 2000 chars → `truncated: true`, length 2000.
- **Concurrency:** two overlapping queries with different `correlation_id`; each response `trace.stages` and `correlation_id` contain only that request (asyncio.gather against a slow embed/rerank fake).
- UI does not `dangerouslySetInnerHTML`.
- HTTP 503 body has no `trace` field.

## Failure Scenarios
Global buffer leftover would mix tenants — the concurrency test must fail if isolation is missing.

## Acceptance Criteria
A reviewer can point at E1, the six named stages, and the correlation id on one 200 response. Two parallel queries do not mix spans.

## Definition of Done
Schema + isolation + tests + inspector UI + Demo + Learning.

## Demo
1. “How much leave?” → six `ok` stages, E1 card, correlation id.
2. Empty collection query → request ok, rest skipped.
3. (Optional) `docker compose logs api | grep <correlation_id>`.

## What I Must Be Able to Explain
Why a process-global span list cannot be a product API. Why skipped rows exist. Why 503 has no trace.
