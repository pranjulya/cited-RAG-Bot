# UI-07 — Hosted Generation

**Status:** TESTED

## Goal
Plug an OpenAI-compatible generator behind the existing port so paraphrase questions can answer in client demos. Citation validation and evidence contract do not change. Heuristic stays CI default.

## Prerequisites
UI-06 COMPLETE.

## References
ADR-009, ADR-011 generation, `GroundedGenerator`, `HeuristicGroundedGenerator`, `CITED_RAG_GENERATION_*`.

## Concepts to Learn
Provider adapters, structured output, timeout fail-closed, never putting API keys in the browser.

## Planned Deliverables
`generation_backend`: `heuristic` | `openai_compatible`. Settings: base URL, model, secret key (server env). Adapter implements the same `GroundedGenerator` port (JSON claims + evidence ids). UI badge: “generator: heuristic | hosted”. No key in frontend env.

## Tasks
1. Adapter + tests with a fake HTTP server (no live billed calls in CI).
2. Timeout → `GENERATION_PROVIDER_ERROR` → 503.
3. Invalid JSON / missing evidence ids → validation still fails closed.
4. Compose/docs: how to point at xAI or OpenAI for a demo; CI unset → heuristic.
5. Learning note.

## Tests
Heuristic still default. Fake hosted success with E1. Fake hosted invents E99 → 422. Timeout → 503. UI shows backend label from a safe settings endpoint **or** from query metadata — do not create a settings leak. Prefer query metadata `model` already on generation result if exposed; if not, a non-secret `GET /ready` or `/v1/meta` with `{generation_backend}` only.

## Failure Scenarios
Missing hosted key with backend=openai_compatible → fail startup or first query 503, not silent heuristic fallback in production. Test env may keep heuristic.

## Acceptance Criteria
With a demo key, a paraphrase of the policy answers and still cites a page. CI remains green without that key.

## Definition of Done
Adapter, fail-closed tests, Demo with hosted key **or** recorded fixture, docs, Learning.

## Demo
1. Show badge heuristic; paraphrase may abstain.
2. Restart API with hosted env (script in phase README).
3. Same paraphrase → ANSWERED + same citation contract + glass box generation stage.
4. Say: “We swapped the brain, not the citation law.”

## What I Must Be Able to Explain
Why fallback-to-heuristic in production would hide outages. Why the model never sees document/page ids. Why keys never go to Vite `VITE_*`.
