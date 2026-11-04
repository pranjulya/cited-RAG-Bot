# ADR-014 — End-User Chat Surface

**Status:** Accepted  
**Date:** 2026-10-31  
**Extends:** ADR-011 and ADR-012. ADR-011 still wins on RAG, citations, auth, and fail-closed retrieval. ADR-012 locks stay in force for the console.

## Context

The glass-box console (ADR-012) is built for operators and technical demos. It shows request IDs, correlation IDs, pipeline stages, and raw evidence on every answer. The product target is now **end users who ask questions about their own HR PDFs**. For them, the console is hard to read.

ADR-012 rejected a **chat-only** UI because it hides ingest state, evidence, no-answer, and deletion. That reason is still valid. This ADR does not replace the console. It adds a second surface for end users that keeps those trust signals visible in plain language.

## Decision

Add an end-user chat surface in the same `web/` app at route `/chat` (and `/chat/{collection_id}`). The console stays at `/` without changes.

## Locked policies

1. **Same app, same API.** The chat lives in `web/src/chat/`. It calls only the existing `/v1/*`, `/health`, and `/ready` routes. No backend change is needed for this phase.

2. **Same auth.** The chat uses the same `Authorization: Bearer <api_key>` and the same `sessionStorage` key as the console. There are no user accounts. This is a known limit for real customers.

3. **Single-turn honesty.** The query API answers each question on its own. The chat shows past turns, but it must not send them to the API or imply that the bot remembers them. The UI says this under the input.

4. **No stored conversations.** The thread lives in React state only. It is lost on reload. Questions and answers are not written to `localStorage` or `sessionStorage`, because they can contain sensitive document text.

5. **Citations stay application-owned.** Each answer shows only API-validated citations, numbered per answer. Clicking a citation opens the source PDF at that page and the evidence text that the API returned for that document version and page range. The UI matches evidence by `document_id`, `document_version_id`, and page overlap, never by file name.

6. **Untrusted text.** Answers and evidence render as text nodes, never `innerHTML`.

7. **Fail-closed stays visible.** `200 INSUFFICIENT_EVIDENCE` shows a plain-language "not in your documents" message plus the reason code. `503` shows a "service unavailable, nothing was answered" message plus the failure code and a retry button. `422 citation_validation_failed` shows that an answer was blocked. These are three different messages.

8. **Ingest is visible.** The document sidebar shows each PDF as Processing, Ready, Failed (with a plain-language reason), or Removing. The input is disabled until at least one document is Ready.

## Alternatives rejected

| Alternative | Why not |
|---|---|
| Replace the console with chat | Loses the operator and teaching surface that ADR-012 built. |
| Move the console off `/` | Breaks existing demos, tests, and screenshots for no product gain in this phase. |
| Send the chat history to the API | The API and citation contract are single-turn. Multi-turn needs its own ADR (query rewriting, history in the prompt, citation scope). |
| Persist threads in browser storage | Stores sensitive document text on the device. |

## Consequences

- End users open `/chat`. Operators keep `/`.
- Real customers still need user accounts, per-tenant keys, and multi-turn questions. Each is a separate decision.
- With the heuristic generator, paraphrased questions can abstain. Hosted generation (UI-07) is recommended for end-user demos.
