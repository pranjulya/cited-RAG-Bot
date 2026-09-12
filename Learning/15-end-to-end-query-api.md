# Phase 15 — End-to-End Query API

## Why orchestration sits outside the route

The route authenticates, loads the collection, and translates domain errors to HTTP. `answer_question` owns retrieval → fusion → rerank → context → no-answer → generation → citation validation. That keeps HTTP details out of the pipeline and lets evaluation call the same function with fakes.

## Domain errors vs provider errors

`INSUFFICIENT_EVIDENCE` is a successful 200 with a reason code. `DENSE_RETRIEVAL_ERROR`, `RERANKER_ERROR`, and `GENERATION_PROVIDER_ERROR` are 503s. `CITATION_VALIDATION_FAILED` is 422 and is never turned into a partial answer. Unauthorized collections stay 404.

## Why partial results must not become success

If generation invents `E99`, returning the rest of the citations would hide fabrication. Fail the request. If dense retrieval times out, do not answer from sparse alone in production.
