# UI-08 — Production Pack

The console is now production-shaped without pretending to be a multi-tenant
SaaS. The `web` service builds the Vite app into a small nginx image, exposes a
healthcheck, and is covered by Compose probes plus a Playwright smoke flow.
The smoke flow mocks the API so CI proves the key gate, collection navigation,
query answer, trace, and narrow-screen layout without a billed model call.

The browser still talks only to FastAPI. CORS is configured from the API
origin, the API key stays in tab-scoped `sessionStorage`, and hosted-generation
credentials stay server-side. Production substitutions still require managed
Postgres/Redis/Qdrant, explicit CORS, and operational secret management.

## Resume wording

“Built a production-shaped cited RAG console with collection-scoped PDF QA,
application-owned page citations, visible retrieval/generation traces, and
fail-closed no-answer behavior.”

## Deliberate V1 limits

This phase does not add SSO, organization/RBAC, OCR, mobile-native clients,
streaming, or a real multi-tenant deployment. Those require separate product
and architecture work.
