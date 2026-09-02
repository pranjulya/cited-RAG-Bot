# Phase 22 — Docker, CI, and Deployment Readiness

**Status:** NOT_STARTED

## Goal
Make the complete system reproducible locally and verifiable in CI with clear dependency readiness and deployment configuration.

## Prerequisites
Phases 00–21 COMPLETE.

## References
HLD deployment/runtime diagram, Phase 00 foundation, `Implementation.md`.

## Concepts to Learn
Container boundaries, service readiness, migrations at deploy time, CI quality gates, environment configuration, reproducible builds.

## Planned Deliverables
Final Dockerfile, compose topology, migration/startup commands, CI workflow, readiness checks, deployment/configuration guide.

## Tasks
1. Containerize API and ingestion worker with shared application image where appropriate.
2. Define PostgreSQL, Redis, Qdrant, and local object-storage dependencies for development.
3. Add dependency health/readiness checks.
4. Document and automate schema migrations.
5. Run lint, format check, type check, unit tests, integration tests, and selected evaluation smoke tests in CI.
6. Validate required environment settings at startup.
7. Ensure secrets remain external to images/repository.
8. Document production substitutions for managed PostgreSQL/Redis/Qdrant/S3-compatible storage.

## Tests
Fresh-clone startup, migrations, service readiness, worker connectivity, CI clean run, missing config failure, container restart behavior.

## Failure Scenarios
Dependency starts late, migration fails, wrong embedding dimension/config, missing secret, stale image/config mismatch.

## Acceptance Criteria
A new engineer can clone the repository, configure documented environment values, start the stack, run tests, and exercise the system reproducibly.

## Definition of Done
Docker/CI verification passes, deployment docs reviewed, Learning notes complete.

## What I Must Be Able to Explain
Liveness vs readiness? Why migrations need deployment discipline? Why environment config must be validated early? What belongs in an image vs secret store?