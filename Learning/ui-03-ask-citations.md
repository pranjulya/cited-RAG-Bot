# UI-03 — Ask + Citations

The query API has two successful shapes: `ANSWERED` carries an application-owned answer and page citations, while `INSUFFICIENT_EVIDENCE` carries a reason and no answer. The console keeps those states distinct from an HTTP `503`, which means query infrastructure is unavailable rather than that the collection lacks evidence.

The public citation object deliberately contains document and page provenance but no `chunk_id`; chunk identity remains an internal validation detail. The UI renders the API response as text nodes and sends only the user question to the collection-scoped query route. Hosted generation is deferred to UI-07; the current heuristic generator is enough to exercise this contract.
