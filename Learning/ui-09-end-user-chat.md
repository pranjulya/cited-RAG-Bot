# UI-09 — End-User Chat

The console answers "why should I trust this answer?" for an engineer. The chat answers the same question for an HR employee. The data is the same. Only the presentation changes.

## Two surfaces, one API

`web/src/main.tsx` checks the path. `/chat` and `/chat/{collection_id}` render `ChatApp`. Every other path renders the console. Both call the same FastAPI routes with the same Bearer key. No backend code changed in this phase.

Mental model: a **surface** is a way of showing a contract. It is not a new contract. If a UI change needs a new API field, that is a backend decision and needs its own phase.

## Single-turn RAG in a chat layout

A chat layout suggests memory. This API has none: each `POST /query` contains only `{"question": ...}`. A follow-up such as "and for part-time staff?" is retrieved on its own and will often abstain.

The chat handles this honestly:

- It sends only the current question (a test checks the request body).
- The hint under the input says that earlier messages are not used.

Multi-turn RAG needs a query-rewrite step ("and for part-time staff?" → "annual leave for part-time staff"), a rule for which earlier citations stay in scope, and an evaluation set for follow-ups. Those are design decisions, not UI work.

## Matching evidence to a citation

The source panel shows the passage that supports a citation. The API returns citations and evidence (`trace.evidence`) as two lists. The UI joins them on:

1. the same `document_id`,
2. the same `document_version_id`,
3. overlapping page ranges.

It never joins on file name. Two uploads named `handbook.pdf` are different documents, so a name join would quote the wrong file. See `matchEvidence` in `web/src/chat/ChatApp.tsx`.

## Failure states in plain language

| API result | What the user sees | Why it is separate |
|---|---|---|
| `200 INSUFFICIENT_EVIDENCE` | "Your documents don't contain a clear answer…" plus the reason code | The system worked. The documents lack the answer. |
| `503` | "The answer service is temporarily unavailable. Nothing was answered." plus the failure code and **Try again** | The system failed. Retrying can help. |
| `422 citation_validation_failed` | "An answer was produced, but its sources could not be verified, so it was blocked." | The guardrail worked. |

If these three are merged into "Sorry, something went wrong", users can no longer tell "not in the policy" from "the system is down". That loses the main trust signal.

## Why the thread is not saved

Questions and answers can quote sensitive HR text. Saving them in `localStorage` would leave that text on a shared device. The thread lives in React state and is lost on reload. A test checks that browser storage contains no question or answer text.

## Race found during testing

If an upload finishes before the first document list request returns, replacing the list with the response drops the new row. The fix merges the response with rows already on screen. A test holds the list request open, uploads, and then releases the list.

## Limits

- One shared API key, no user accounts.
- The heuristic generator copies the evidence text. It does not write an answer in its own words, and paraphrased questions can abstain. Use hosted generation for end-user demos.
- Headless browsers show the PDF frame blank (no built-in viewer). The quoted passage and the "Open PDF in a new tab" link still work.
