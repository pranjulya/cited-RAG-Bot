# Jev Shadow Decision Layer — Implementation Plan

**Date:** 2026-09-22
**Design:** `docs/superpowers/specs/2026-09-22-jev-shadow-decision-layer-design.md`
**Branch:** `codex/jev-shadow`
**PR target:** `main`

## Outcome

Add an opt-in TypeSafe Jev adapter that evaluates the existing evidence package
in shadow mode. The existing query answer, citations, no-answer behavior, HTTP
contract, and UI remain authoritative and unchanged.

## Execution rules

- Work only in `/private/tmp/cited-rag-jev-shadow`.
- Keep the default backend disabled; CI must make no provider call.
- Use test-first slices: failing deterministic test, minimum implementation,
  focused tests, then the full relevant suite.
- Verify the exact TypeSafe System One request/response schema before writing
  the adapter parser. Do not guess provider fields.
- Do not add a provider SDK or expose provider payloads outside the adapter.
- Do not enable Jev-controlled routing in this phase.

## Task 1 — Record the architecture decision and phase contract

Files:

- Add `docs/architecture/decisions/ADR-013-jev-shadow-decision-layer.md`.
- Add `implementation/jev/jev-01-shadow.md` with status `IN_PROGRESS`.
- Add `Learning/jev-01-shadow.md` and link it from `Learning/README.md`.

Content:

- Adapter/provider boundary and timeout ownership.
- Model input restricted to question plus application-created `E1..En` labels
  and evidence text.
- Shadow failures are observable but never become insufficient evidence.
- Jev cannot create citations or override application-owned decisions.
- Phase definition of done and exact verification commands.

Check:

```text
git -c core.fsmonitor=false diff --check
```

## Task 2 — Add the normalized decision contract

Write tests first in `tests/unit/test_jev_decision.py` for:

- probability bounds `[0, 1]`;
- normalized `answerable` and `model` fields;
- evidence serialization containing only `id` and `text`.

Implement the smallest reusable contract:

- `src/cited_rag/domain/models/decision.py` — immutable `EvidenceDecision`.
- `src/cited_rag/ports/decision.py` — async `EvidenceDecisioner` protocol.
- `src/cited_rag/domain/exceptions.py` — `DecisionProviderError` with a stable
  failure code, without changing existing query behavior.

Do not add a general provider framework or a factory abstraction beyond the one
implementation required here.

## Task 3 — Implement the TypeSafe adapter

Write adapter tests first in `tests/unit/test_typesafe_decision.py` using a
fake/monkeypatched transport:

- valid System One response maps to `EvidenceDecision`;
- malformed response is rejected;
- non-2xx response is rejected;
- timeout/transport failure maps to `DecisionProviderError`;
- request body contains only the question and `E1..En` text;
- API key is sent as a Bearer header and never appears in exceptions.

Before implementation, confirm the current official schema at
`https://api.typesafe.ai/docs` and capture the verified fields in the adapter
test fixture. Then add:

- `src/cited_rag/adapters/decision/typesafe.py` using the existing stdlib HTTP
  pattern;
- `src/cited_rag/adapters/decision/__init__.py` with a minimal constructor;
- no direct provider imports in application or API modules.

The adapter should accept `base_url`, `api_key`, `model`, and timeout, and map
provider-specific Noul/probability data to the normalized contract.

## Task 4 — Add disabled-by-default settings and application wiring

Extend `src/cited_rag/config.py` with:

- `jev_shadow_enabled: bool = False`;
- `jev_base_url`;
- `jev_model: str = "typesafe/jev-1.13"`;
- `jev_api_key: SecretStr | None`;
- `jev_timeout_seconds` with a positive bound.

Add settings tests in `tests/unit/test_config.py` for disabled defaults,
custom values, and enabled-without-key failure. Preserve production secret
validation and existing settings behavior.

Wire `src/cited_rag/main.py` so `app.state.jev_decisioner` is either `None` or
the TypeSafe adapter. Add factory tests; default test/application startup must
remain provider-free.

## Task 5 — Integrate shadow observation into the query pipeline

Write query tests first, extending the existing query/no-answer test module:

- successful Jev shadow observation leaves the deterministic `QueryOutcome`
  unchanged;
- Jev provider failure leaves the same outcome and citations unchanged;
- no evidence skips the provider call;
- the evidence payload contains only `E1..En` and text;
- the public query response and six locked trace stages remain unchanged.

Add the smallest application helper, likely in
`src/cited_rag/application/query.py` or a dedicated small observation module,
that:

1. runs after `build_evidence_package`;
2. invokes the optional decisioner with a bounded timeout;
3. records an internal span and counters for called/skipped/failed;
4. logs only correlation ID, model, normalized decision, probability, and
   baseline outcome;
5. swallows only `DecisionProviderError` so the existing answer path remains
   authoritative.

Do not add `jev` to the public `QUERY_STAGES` tuple in this phase.

## Task 6 — Add evaluation comparison hooks

Write deterministic evaluation tests using a fake decisioner and a small
fixture. Extend `src/cited_rag/evaluation/run.py` and related models only as
needed to report:

- Jev/baseline agreement;
- false-answer and abstention disagreement;
- mean/provider latency and failure count;
- raw probability values needed for later calibration.

Keep the existing retrieval, generation, citation, and no-answer metrics
unchanged. The Jev comparison is opt-in and must not require a live key.

## Task 7 — Documentation and learning notes

Complete:

- `implementation/jev/jev-01-shadow.md` status and definition of done;
- `Learning/jev-01-shadow.md` concepts: typed probabilistic decisions,
  shadow evaluation, provider adapters, calibration, and fail-closed
  application ownership;
- `Learning/README.md` index entry;
- `.env.example` entries with a placeholder only, never a real key;
- operator documentation describing opt-in shadow mode and its latency/cost.

## Task 8 — Verification and end-to-end testing

Run, in order:

```text
./.venv/bin/ruff check src tests
./.venv/bin/ruff format --check src tests
./.venv/bin/mypy src
./.venv/bin/pytest tests/unit/test_jev_decision.py tests/unit/test_typesafe_decision.py tests/unit/test_config.py -q
./.venv/bin/pytest tests/unit -q
./.venv/bin/pytest tests/integration/test_query_api.py -q
git -c core.fsmonitor=false diff --check
```

Add an API-level end-to-end test with a fake Jev provider and shadow enabled;
assert the existing answer, citations, status, and trace schema are identical
to the non-Jev path. Add a separately marked live smoke command that runs only
when `CITED_RAG_JEV_API_KEY` is explicitly present; never make it part of the
default CI job.

## Task 9 — Review, PR, and handoff

Before claiming completion:

1. Review the diff for collection scoping, secret safety, provenance leakage,
   and accidental behavior changes.
2. Update the phase status only after all required tests pass.
3. Commit the implementation and documentation on `codex/jev-shadow`.
4. Push the branch and open one PR into `main`.
5. Update `MEMORY.md` on the phase branch with the current state and complete
   Jev phase record, including exact verification results.

The next phase must not enable Jev-controlled routing until the shadow PR is
merged and its evaluation results are reviewed.

## Definition of done

- Jev is disabled by default and server-keyed when enabled.
- Only a provider adapter knows the TypeSafe payload shape.
- Model input contains no trusted provenance identifiers.
- Shadow provider success/failure cannot alter current answers or citations.
- Default unit, integration, lint, format, type, and diff checks pass.
- The fake-provider end-to-end test proves the unchanged public contract.
- ADR, phase documentation, Learning notes, and `MEMORY.md` are updated.
- A reviewable PR is open against the merged `main`.
