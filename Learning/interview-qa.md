# Interview Q&A

## How does a PDF page become a public citation?

Parse to page rows → chunk with `page_start`/`page_end` → embed/encode onto the chunk UUID in Qdrant → retrieve/fuse/rerank → context builder assigns `E1` and keeps provenance server-side → model may only emit `E1` → validator maps `E1` to `{document_id, document_version_id, document_name, page_start, page_end}`. `chunk_id` never leaves the API.

## Dense vs sparse vs hybrid?

Dense finds paraphrases. Sparse finds identifiers and rare tokens. Raw scores are incomparable, so V1 fuses ranks with RRF in application code. Qdrant native fusion is out so each list stays observable.

## Why rerank?

First-stage retrieval maximizes recall. A cross-encoder (or the overlap fake in tests) reorders a shortlist for precision. Timeout is `RERANKER_ERROR`, not “just use fused order.”

## How is RAG evaluation layered?

Parsing/provenance, retrieval (Recall@K/MRR/nDCG), rerank lift, answer grounding, citation validity vs correctness, no-answer precision/recall. A bad answer is not automatically a bad LLM.

## Why is no-answer a success?

If the PDFs do not contain the policy, inventing one is worse than abstaining. `INSUFFICIENT_EVIDENCE` is 200 with a reason code. Provider outages are 503s.

## How do you stop citation fabrication?

Unknown `E#` → `CITATION_VALIDATION_FAILED`. No strip-and-answer. Model never sees document/page/chunk ids.

## Key production failures?

Qdrant down at query, rerank timeout, generation timeout, partial index (no READY), delete crash after tombstone (cleanup retries), prompt injection in PDF text, cross-collection UUID guessing (404).
