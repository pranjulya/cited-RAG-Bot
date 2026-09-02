# Phase 18 — Security Hardening

**Status:** NOT_STARTED

## Goal
Harden the portfolio deployment against cross-collection leakage, malicious PDFs, prompt injection, abusive requests, and secret exposure.

## Prerequisites
Phases 15–17 COMPLETE.

## References
PRD security requirements, HLD security architecture, LLD security rules.

## Concepts to Learn
Authentication vs authorization, tenant isolation, untrusted document content, prompt injection, resource limits, secret management, secure logging.

## Planned Deliverables
Portfolio auth boundary, collection authorization middleware/service, hardened upload limits, query limits, secret validation, adversarial security tests.

## Tasks
1. Harden the API-key and collection-ownership controls introduced in Phases 00/02 (do not introduce auth here for the first time).
2. Enforce collection filters in every retrieval path.
3. Add upload size/type/signature/resource limits.
4. Add request/query length and concurrency limits.
5. Validate secrets/config are not committed or logged.
6. Test document text that attempts to override system instructions.
7. Test unauthorized access and cross-collection evidence/citation leakage.
8. Review object-storage and DB credentials for least privilege.

## Tests
Unauthorized upload/query/delete, cross-collection retrieval attempt, prompt injection PDF, oversized/malformed file, secret redaction, abuse-limit behavior.

## Failure Scenarios
Filter omitted in one retriever, malicious PDF resource exhaustion, prompt injection succeeds, secret appears in logs.

## Acceptance Criteria
Security controls fail closed on authorization boundaries and adversarial documents cannot elevate retrieved text to trusted instructions.

## Definition of Done
Security tests, threat review, docs, Learning notes complete.

## What I Must Be Able to Explain
Authentication vs authorization? Retrieval-time tenant filtering? Why RAG prompt injection is different from user prompt injection? Why retrieved documents are untrusted?