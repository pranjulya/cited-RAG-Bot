# UI-09 — End-User Chat

**Status:** TESTED

## Goal
Give end users a chat screen at `/chat` where they upload their HR PDFs, ask questions, and check each answer against the cited PDF page. The console at `/` does not change.

## Prerequisites
UI-08 merged to `main`. ADR-014 accepted.

## References
ADR-011, ADR-012, ADR-014, `web/src/App.tsx` (console behavior to match for polling, errors, and 401).

## Concepts to Learn
Route-level surfaces in one SPA, single-turn vs multi-turn RAG, evidence-to-citation matching by identity, plain-language failure states.

## Planned Deliverables
- `web/src/chat/ChatApp.tsx`, `web/src/chat/types.ts`, `web/src/chat/chat.css`
- `web/src/main.tsx` picks the chat for `/chat` and `/chat/{collection_id}`
- Vitest tests in `web/src/chat/ChatApp.test.tsx`
- Playwright smoke in `web/tests/chat.spec.ts` (mocked API)
- README section and `Learning/ui-09-end-user-chat.md`

## Tests
- Key gate; 401 signs out.
- Upload → Processing → Ready; input disabled until Ready.
- Answered turn shows numbered citations; clicking one shows the matched evidence and fetches the PDF.
- Evidence with the same file name but another document ID is not shown.
- `INSUFFICIENT_EVIDENCE`, `503`, and `422` show three different messages.
- Thread is not written to browser storage.

## Failure Scenarios
Stale responses after switching knowledge base. Blob URL leaks. Long answers with line breaks. Narrow screens.

## Demo
1. Open `http://localhost:8080/chat`, enter the key.
2. Create "HR policies", add `samples/acme-hr-policy.pdf`, wait for Ready.
3. Ask "How many days of paid annual leave do employees get?" and open source [1].
4. Ask "What is the dress code?" and show the "not in your documents" reply.

## Acceptance Criteria
A non-technical user can run the demo without reading request IDs or pipeline stages, and every answer can be checked against its PDF page.
