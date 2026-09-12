# Phase 14 — No-Answer Decision Policy

## Why abstention is a success case

A correct “I don’t know from these PDFs” is better than a fluent wrong policy. `INSUFFICIENT_EVIDENCE` is a 200-shaped outcome with a reason code, empty citations, and no fabricated pages. It is scored separately from infrastructure errors.

## No-answer precision vs recall

Precision: of the times we abstain, how often was the question truly unanswerable? Recall: of truly unanswerable questions, how often did we abstain? A high min-rerank threshold raises abstention recall and can hurt answer recall. `CITED_RAG_MIN_RERANK_SCORE` stays at 0 until evaluation sets a baseline.

## Why thresholds come from evaluation

Picking 0.7 because it “feels right” over-refuses or under-refuses depending on the reranker’s score scale. Overlap scores are token counts, not probabilities. Phase 19/20 must measure false-answer rate and no-answer precision before tightening the knob.

Provider timeouts stay `GENERATION_PROVIDER_ERROR` / `RERANKER_ERROR` / retrieval errors. They are never rewritten as `INSUFFICIENT_EVIDENCE`. Zero READY documents use reason `NO_READY_DOCUMENTS`.
