# UI-07 — Hosted Generation

Hosted generation is a provider adapter, not a new query path. The
OpenAI-compatible adapter receives the existing trusted system prompt,
question, and evidence JSON, then normalizes structured JSON into the same
`GroundedGenerationResult` used by the heuristic generator.

The server owns the provider URL, model, and secret key. The browser receives
only the non-secret `generation_backend` label (`heuristic` or
`openai_compatible`, rendered as `hosted`). A missing hosted key fails startup;
there is no production fallback to heuristic generation that could hide a
provider outage.

Timeouts and transport/malformed-response errors become the existing
`GENERATION_PROVIDER_ERROR` 503 path. Unknown or missing evidence IDs remain
inside the existing citation validator, so hosted generation cannot weaken the
application-owned citation contract.
