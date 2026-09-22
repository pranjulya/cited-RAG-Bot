# Jev Shadow Decision Layer

**Date:** 2026-09-22
**Status:** Draft — design review required
**Branch:** `codex/jev-shadow`

## Goal

Add an opt-in, shadow-only TypeSafe Jev integration to the query pipeline. Jev
will return a typed answerability decision for the already-built evidence
package. The decision will be recorded for comparison and evaluation, but it
will not change the answer, citations, HTTP status, or existing no-answer
policy.

TypeSafe positions Jev as a structured-decision model with typed probabilistic
outputs, rather than a prose generator ([overview](https://typesafe.ai/blog/introducing-system-one-models-and-jev)).
The integration will use the documented System One API boundary
([API](https://api.typesafe.ai/docs)) and keep provider-specific payloads
inside an adapter.

## Scope

This phase includes:

- one normalized decision contract: `answerable` plus its calibrated
  probability;
- one `EvidenceDecisioner` port and a TypeSafe adapter using
  `POST /v1/systemone`;
- server-only settings for enabling Jev, selecting `typesafe/jev-1.13`, the
  base URL, API key, and timeout;
- one query-pipeline call after evidence construction and before generation;
- bounded shadow observability and deterministic tests;
- evaluation hooks that can compare Jev's decision with the existing golden
  dataset labels.

## Explicit non-goals

- Jev does not generate or rewrite answers.
- Jev does not select or create authoritative citations.
- Jev does not receive document IDs, page numbers, chunk IDs, storage URIs, or
  other provenance identifiers.
- Jev does not control abstention, retrieval, generation, or HTTP responses in
  this phase.
- No UI or public `QueryResponse` schema changes.
- No provider SDK dependency; use the existing stdlib HTTP adapter pattern.
- No persistence table, queue, retry system, or background worker for shadow
  results.
- No numeric production threshold is chosen before baseline evaluation.

## Placement in the existing pipeline

The call is made after:

```text
hybrid retrieval → reranking → evidence package
```

and before the existing deterministic `decide_before_generation` check. This
allows comparison on both answerable and deterministic no-answer cases while
leaving the current decision path authoritative.

If there are no evidence records, Jev is skipped because there is no model
input to evaluate. If the provider times out, returns an invalid payload, or
is unavailable, the query continues on the existing path and records a
shadow-provider failure. Provider failures must never become
`INSUFFICIENT_EVIDENCE`.

The first implementation may await the adapter with a short configured
timeout. This keeps lifecycle and error handling simple; if measured latency
is unacceptable, moving shadow calls off the request path is a later change,
not part of this phase.

## Normalized contract

The application-facing port should expose only normalized domain data, for
example:

```text
EvidenceDecisioner.decide(question, evidence) -> EvidenceDecision

EvidenceDecision
  answerable: bool
  answerable_probability: float  # inclusive range [0, 1]
  model: str
```

The adapter may use TypeSafe's `Noul`/probability representation internally,
but provider schemas must not leak into application code. The implementation
must verify the exact request and response fields against the live API schema
before writing the adapter. An unexpected model response is a provider error,
not an answerability decision.

## Model-visible input boundary

The adapter sends only:

```json
{
  "question": "...",
  "evidence": [
    {"id": "E1", "text": "..."},
    {"id": "E2", "text": "..."}
  ]
}
```

The `id` values are the application-created evidence labels. The adapter must
not serialize the `EvidenceRecord` object directly. This preserves ADR-011's
rule that model input contains evidence labels and text, never trusted
document/page/chunk identity.

## Configuration

The default remains disabled so existing tests, local development, and CI make
no external call. Proposed server-only settings:

```text
CITED_RAG_JEV_SHADOW_ENABLED=false
CITED_RAG_JEV_BASE_URL=https://api.typesafe.ai
CITED_RAG_JEV_MODEL=typesafe/jev-1.13
CITED_RAG_JEV_API_KEY=<secret>
CITED_RAG_JEV_TIMEOUT_SECONDS=2
```

When shadow mode is enabled, a missing or placeholder API key fails startup,
matching the existing hosted-generation policy. The key is never returned in
API responses, logs, traces, or evaluation manifests.

## Observability and evaluation

Shadow calls record:

- call/skip/failure counters;
- bounded provider latency through the existing span/metrics mechanism;
- model name, normalized decision, probability, baseline outcome, and
  correlation ID in structured metadata only.

Raw questions, PDF text, and provider payloads are not logged. The existing
six-stage public query trace remains unchanged; any Jev span is internal and
ignored by the locked response-stage list.

The evaluation harness will add an opt-in comparison result for each golden
case, using the existing `answerable` labels. The first report should expose
agreement, false-answer/abstention disagreement, latency, provider failures,
and probability calibration data. Release thresholds are deferred until a
baseline exists.

## Testing and end-to-end gate

The implementation phase must include:

1. adapter contract tests for valid, malformed, timeout, and non-2xx provider
   responses;
2. payload tests proving only `question` plus `E-ID`/text reaches the adapter;
3. query tests proving shadow success and failure leave the existing outcome
   and citations unchanged;
4. settings/factory tests for disabled-by-default and missing-key behavior;
5. evaluation tests proving the comparison output is deterministic with a fake
   decisioner;
6. an end-to-end API test with shadow enabled and a fake provider, asserting
   the existing answer/citation contract is unchanged;
7. an optional live TypeSafe smoke test, run only when an explicit API key is
   supplied and never as the default CI test.

## Architecture and governance

This is a new provider boundary and therefore requires a Jev ADR (or an
explicit amendment to ADR-009) before implementation is merged. The ADR must
record the adapter boundary, model-input restriction, fail-open-for-behavior
but fail-visible-for-observability shadow policy, and the rule that Jev cannot
override application-owned citations or no-answer decisions.

The implementation will be planned as one phase and one pull request after
this design is approved. A later phase may enable Jev-controlled routing only
after calibration and review of the shadow evaluation results.

## Design review checklist

- [ ] Shadow-only behavior is approved.
- [ ] The single answerability decision is sufficient for Phase 1.
- [ ] The model-visible input boundary is correct.
- [ ] The no-public-schema-change constraint is acceptable.
- [ ] The ADR approach is approved.
- [ ] The implementation plan may be written.
