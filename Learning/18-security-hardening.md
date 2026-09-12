# Phase 18 — Security Hardening

## Authentication vs authorization

Authentication: the caller presents a valid API key. Authorization: that principal owns the collection. A guessed `collection_id` still 404s. Collection filters inside Qdrant are a second fence; they do not replace the ownership check.

## Why RAG prompt injection is different

Classic jailbreaks target the user message. Here the hostile text is *retrieved evidence*. The model is told to treat it as data. Tests use a PDF that says “ignore the system prompt”; the pipeline must still abstain unless the evidence actually answers the question.

## Why documents are untrusted

Anyone who can upload a PDF can put instructions, secrets, or other tenants’ names in it. Provenance mapping, evidence IDs, and citation validation exist so the model cannot mint pages or collections it was not given.
