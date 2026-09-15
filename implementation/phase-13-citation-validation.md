# Phase 13 — Citation Mapping and Validation

**Status:** REVIEWED
**On main:** merged PR #18. **Not COMPLETE:** AGENTS.md COMPLETE requires a recorded Definition of Done (implementation, tests, review, docs, Learning) at close-out; that was not recorded.

## Goal
Convert model-selected evidence IDs into authoritative document/page citations and reject fabricated or unauthorized references before response delivery.

## Prerequisites
Phase 12 COMPLETE.

## References
ADR-006, PRD FR-12/13, HLD Citation Validator, LLD citation mapping.

## Concepts to Learn
Deterministic validation, provenance mapping, citation validity vs correctness vs completeness, authorization boundaries.

## Planned Deliverables
Citation validator service, evidence-ID lookup, external citation DTO, validation error taxonomy.

## Tasks
1. Validate every returned evidence ID exists in the request evidence map.
2. Resolve chunk → document version → PDF page from authoritative metadata.
3. Verify collection membership and document version validity.
4. Unknown or unapproved evidence IDs fail the request with `CITATION_VALIDATION_FAILED`. Do not repair or strip-and-answer.
5. Render external citation with `document_id`, `document_version_id`, `document_name`, `page_start`, `page_end`. Do not expose `chunk_id`.
6. Record citation-validation outcome for telemetry/evaluation.

## Tests
Valid citation, unknown E-ID, cross-collection mapping attempt, stale/deleted document, duplicate IDs, model-invented page number ignored/rejected.

## Failure Scenarios
Missing DB provenance, inconsistent mapping, deleted document between generation and validation.

## Acceptance Criteria
No unvalidated model-generated provenance reaches the API response.

## Definition of Done
Validator unit/integration tests, review, docs, Learning notes complete.

## What I Must Be Able to Explain
Citation validity vs semantic correctness? Why application-owned mapping is safer than trusting model page numbers?