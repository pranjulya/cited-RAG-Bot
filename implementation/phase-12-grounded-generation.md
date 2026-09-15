# Phase 12 — Grounded Generation

**Status:** TESTED
**On main:** merged PR #17. **Not REVIEWED:** GitHub PRs #2–#29 have no submitted reviews. **Not COMPLETE:** AGENTS.md DoD was not recorded at close-out.

## Goal
Generate answers strictly from approved evidence using a provider-neutral LLM adapter and structured citation output.

## Prerequisites
Phase 11 COMPLETE.

## References
PRD FR-11/14, ADR-006/009, HLD Grounded Generation, security requirements.

## Concepts to Learn
Grounding prompts, structured output, prompt injection boundaries, provider abstraction, token/latency telemetry, refusal/no-answer behavior.

## Planned Deliverables
Generation provider port, default adapter, grounded prompt builder, structured answer model containing answer/status/evidence IDs.

## Tasks
1. Separate trusted system instructions from untrusted PDF evidence.
2. Require answer based only on supplied evidence.
3. Allow citations only from `E1..En` supplied for the request. Prompt evidence is ID + text only (no document/page/chunk ids).
4. Define structured `ANSWERED` and `INSUFFICIENT_EVIDENCE` outputs.
5. Add provider timeout/rate-limit/error translation.
6. Record model, latency, token usage, and configuration metadata.
7. Add prompt-injection fixtures where PDF text asks the model to ignore system rules.

## Tests
Grounded answer, insufficient evidence, unknown evidence ID output, provider timeout, malformed structured output, prompt injection content.

## Failure Scenarios
Rate limit, timeout, malformed response, model ignores evidence constraint, prompt injection attempt.

## Acceptance Criteria
Generation cannot legitimately reference evidence identities outside the provided request context.

## Definition of Done
Provider contract, deterministic tests, security cases, telemetry, review, Learning notes complete.

## What I Must Be Able to Explain
Grounding vs hallucination? Why retrieved text is untrusted? Why structured output helps but does not replace validation?