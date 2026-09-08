# Phase 17 — Observability

## Logs vs metrics vs traces

Logs explain one request (`correlation_id`, stage, failure code). Metrics count events (`query.no_answer`) without attaching UUIDs as labels. Traces/spans name the LLD stages (`query.rerank`, `query.generation`) so latency is attributable. This phase standardizes names and redaction; stages already logged from Phases 03–15.

## Why high-cardinality labels hurt

Putting `chunk_id` or `question` on a Prometheus label creates a new time series per value and can take down the metrics backend. IDs belong in logs/traces. Counters use low-cardinality names only.

## Why RAG needs stage-level tracing

A bad answer can be a parse miss, a retrieval miss, a fusion miss, a rerank bury, a budget drop, or a generation skip. One “query_latency_ms” number cannot tell you which. Stage counts and latencies localize the failure without dumping PDF text.
