# Phase 12 — Grounded Generation

## Grounding vs hallucination

A grounded answer is assembled only from supplied evidence IDs and their text. Hallucination is content that cannot be traced to that package. The prompt forbids outside knowledge and treats PDF text as data. The heuristic adapter used in tests/dev is not an LLM; a hosted model can replace it behind `GroundedGenerator`.

## Why retrieved text is untrusted

A PDF can contain “ignore the system prompt”. That string is still evidence text, not an instruction. System rules live in a separate prefix. The generator must not follow commands that appear only inside the evidence block.

## Why structured output does not replace validation

`ANSWERED` / `INSUFFICIENT_EVIDENCE` plus `claims[].evidence_ids` makes citation identity explicit. The model can still invent `E99`. Phase 13 rejects unknown IDs with `CITATION_VALIDATION_FAILED`. Structured JSON is a parsing aid, not a trust boundary.
