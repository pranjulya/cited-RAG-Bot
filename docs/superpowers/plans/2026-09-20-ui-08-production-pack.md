# UI-08 Production Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the glass-box console reproducible as a production-shaped demo with a tested web image, browser smoke coverage, responsive presentation, and operator documentation.

**Architecture:** Keep the existing Vite/React static site and FastAPI boundary. Extend CI and Compose verification around the existing `web` image; do not add backend features or expose secrets to the browser.

**Tech Stack:** Vite, React, TypeScript, Vitest, Playwright, Docker Compose, nginx, GitHub Actions.

**Spec:** `implementation/ui/ui-08-production-pack.md`, `docs/architecture/decisions/ADR-012-glass-box-console.md`.

## Global Constraints

- Browser talks only to FastAPI and stores the API key in tab-scoped `sessionStorage`.
- Heuristic generation remains the CI/default backend; hosted keys stay server-side.
- Collection scope, evidence IDs, page citations, and fail-closed 503/200 behavior remain unchanged.
- No real employee PDFs or secrets in screenshots, fixtures, images, or logs.

## Review Focus

- Web image must serve SPA deep links and pass its healthcheck.
- Browser smoke must prove the key gate and collection flow without depending on a hosted model.
- Narrow viewport must keep the ask/trace/page-proof surfaces usable.
- Compose must wait for `web` and probe both UI and API origins.
- Deployment docs must explain explicit production CORS and server-only generator settings.

### Task 1: Browser smoke and package scripts

**Files:** `web/package.json`, `web/package-lock.json`, `web/playwright.config.ts`, `web/tests/smoke.spec.ts`, `.github/workflows/ci.yml`

- Add `@playwright/test` and a smoke script.
- Use route mocks for health, collections, documents, and query so CI proves UI behavior without a billed provider.
- Run Chromium headless in CI; retain traces/screenshots only on failure.
- Keep existing Vitest and typecheck jobs green.

### Task 2: Responsive presentation

**Files:** `web/src/styles.css`, `web/src/App.test.tsx`

- Add the smallest media-query/layout rules needed for tables, badges, forms, trace evidence, and PDF proof at narrow widths.
- Add a deterministic render assertion for the trace/page-proof labels used by the smoke flow.

### Task 3: Compose and CI production checks

**Files:** `docker-compose.yml`, `.github/workflows/ci.yml`, `docs/operations/deployment.md`

- Keep the existing nginx web image and healthcheck, making its API base explicit and documented.
- Add a CI web-image/browser smoke path and make compose-smoke verify the UI origin plus API readiness.
- Document UI origin/CORS, production substitutions, and the hosted generator environment without putting keys in image layers.

### Task 4: Demo and learning documentation

**Files:** `README.md`, `Learning/ui-08-production-pack.md`, `Learning/README.md`, `MEMORY.md`, `implementation/ui/ui-08-production-pack.md`

- Add a 10-minute client script, screenshot-safe capture instructions, resume wording, and production-shaped limitations.
- Mark UI-08 `TESTED` only after the phase checks pass; record exact commands and known gaps in `MEMORY.md`.

## Verification

Run `npm ci`, `npm test -- --run`, `npm run build`, Playwright smoke, Python unit/lint/type checks, `docker compose config`, and `git diff --check`. Do not claim completion until the phase PR is opened and the memory handoff is committed on the phase branch.
