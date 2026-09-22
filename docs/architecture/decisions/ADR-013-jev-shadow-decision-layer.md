# ADR-013 — Jev Shadow Decision Layer

**Status:** Accepted for Phase JEV-01 shadow implementation
**Date:** 2026-09-22
**Extends:** ADR-009 provider boundaries and ADR-011 V1 locked policies

## Context

The query pipeline already builds a collection-scoped evidence package with
application-owned `E1..En` labels before deterministic no-answer checks and
grounded generation. TypeSafe Jev can provide a typed, probabilistic judgment
about that evidence, but it must not become a second citation or answer
authority before its behavior is measured.

## Decision

Add an opt-in `EvidenceDecisioner` port with a TypeSafe adapter. Phase JEV-01
uses the adapter only in shadow mode after evidence construction. The adapter
returns one normalized answerability probability. Jev results are recorded for
comparison; the existing query outcome remains authoritative.

## Locked boundaries

1. The default is disabled and makes no external provider call.
2. Provider-specific request/response fields stay inside the adapter.
3. Model input contains only the question and application-created `E1..En`
   labels plus evidence text. It never contains document, version, page,
   chunk, or storage identifiers.
4. Jev cannot generate answers, create citations, change no-answer decisions,
   or change HTTP responses in this phase.
5. Provider errors are observable and fail open for the existing application
   path; they never become `INSUFFICIENT_EVIDENCE`.
6. The public query response and six locked UI trace stages do not change.
7. No confidence threshold is enabled until a versioned golden evaluation
   establishes a baseline.

## Consequences

- Query requests may incur the configured shadow timeout while enabled.
- A real API key is required only for explicitly enabled environments and is
  never returned or logged.
- The next phase may evaluate routing or abstention, but requires this phase's
  shadow results and a new review before changing behavior.
