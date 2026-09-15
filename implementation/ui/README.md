# UI implementation — Glass-Box Console

**Status:** PLANNING COMPLETE, ADR-012 DRAFTED, UI-00 NOT_STARTED

This folder is the execution layer for the console. Backend RAG remains `implementation/phase-00` … `phase-23`. Do not implement UI-N until UI-(N-1) is merged to `main` (same rule as backend).

## Authoritative docs

1. `MEMORY.md` (Current state)
2. `docs/architecture/decisions/ADR-011-v1-locked-policies.md`
3. `docs/architecture/decisions/ADR-012-glass-box-console.md`
4. `docs/product/glass-box-console.md`
5. this file and the current `implementation/ui/ui-XX-*.md`

## Status model

`NOT_STARTED → IN_PROGRESS → IMPLEMENTED → TESTED → REVIEWED → COMPLETE`

`COMPLETE` means implementation, automated tests, the phase **Demo** script, review, and Learning notes.

## Git

Never commit to `main`. Branch names: `ui-00-foundation`, `ui-01-collections`, … Open a PR into `main`. One UI phase per branch.

## Phase index

| Phase | Name | Depends on | Client demo (one line) |
|---|---|---|---|
| UI-00 | Foundation | Backend on `main` | Browser: key gate + live health/ready |
| UI-01 | Collections | UI-00 | Create “Acme HR”, see it listed |
| UI-02 | Ingest theater | UI-01 | Drop a text PDF, watch READY |
| UI-03 | Ask + citations | UI-02 | Question → answer + page citations or abstain |
| UI-04 | Glass box | UI-03 | Stages, E-IDs, correlation id on that request |
| UI-05 | Page proof | UI-04 | Click citation → that PDF page |
| UI-06 | Fail-closed studio | UI-05 | Scan fail, abstain, delete, 503 vs 200 |
| UI-07 | Hosted generation | UI-06 | Paraphrase answers with hosted model; citations still validated |
| UI-08 | Production pack | UI-07 | Compose `web` in CI, screenshots, resume copy, deploy notes |

## Invariants

- UI talks only to FastAPI.
- Collection scoping and citation validation never weaken.
- PDF text is untrusted data.
- Heuristic generator remains the CI default.
- Do not implement a later UI phase on an earlier branch.

## Learning

Each UI phase adds `Learning/ui-XX-*.md` when implemented. Phase UI-08 indexes them.
