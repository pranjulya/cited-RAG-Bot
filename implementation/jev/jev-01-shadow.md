# JEV-01 — Jev Shadow Decision Layer

**Status:** TESTED

## Goal

Call TypeSafe `typesafe/jev-1.13` after evidence construction and record a
typed answerability decision without changing the existing answer, citation,
no-answer, or HTTP behavior.

## Prerequisites

- V1 backend and UI phases are merged to `main`.
- ADR-013 is accepted for this implementation.
- Work starts from the merged `main` commit on `codex/jev-shadow`.

## Definition of done

- Jev is disabled by default and uses server-only configuration.
- The provider adapter receives only question plus `E1..En` evidence text.
- Adapter failures are visible in metrics/log metadata but do not alter query
  outcomes.
- Unit, integration, lint, format, type, and end-to-end fake-provider tests
  pass.
- Learning notes and `MEMORY.md` are updated after the PR is opened.

## Verification

The exact commands are recorded in the implementation plan:
`docs/superpowers/plans/2026-09-22-jev-shadow-decision-layer.md`.
