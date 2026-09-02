# ADR-006 — Citation Contract and Validation

**Status:** Accepted  
**Decision:** Citation identity is created and owned by the application. The LLM may reference only evidence IDs supplied in the prompt; the application resolves those IDs to document/page/chunk metadata and validates them before returning a response.

## Context

Allowing the model to freely emit page numbers or source identifiers makes fabricated citations possible even when the generated answer sounds correct.

## Decision

The context builder assigns each approved evidence item a request-scoped identifier such as `E1`, `E2`, etc.

Example evidence supplied to the LLM:

```text
[E1]
Evidence:
"Employees are entitled to ..."
```

Do not send `document_id`, `chunk_id`, or page numbers to the model. Provenance stays in the server-side evidence map. The model may cite only evidence IDs such as `E1`.

The response pipeline then:

1. parses cited evidence IDs;
2. verifies each ID was in the approved context;
3. maps the ID deterministically to persisted provenance;
4. if any cited evidence ID is unknown or was not approved for this request, fail with `CITATION_VALIDATION_FAILED` (V1 does not repair or strip-and-answer);
5. returns external citation objects with document id, document version, document name, and page range (not `chunk_id`).

## Important Distinction

Citation validation answers: "Is this citation real and was the evidence supplied?"

Citation correctness answers: "Does this evidence actually support the claim?"

The first is enforced in the runtime pipeline. The second is primarily measured by the evaluation harness in V1.

## Consequences

- The model does not control citation identity.
- Every returned citation is traceable to retrieved evidence.
- Claim-to-citation completeness still requires evaluation.
- Context builder, generator, validator, and API response share a stable evidence contract.

## Validation Required

Tests must cover invented IDs, citations to retrieved-but-not-approved chunks, wrong document/page mapping, duplicated citations, and insufficient-evidence responses.