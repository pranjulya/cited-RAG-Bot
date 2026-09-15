# UI-00 — Foundation

The console is a static SPA. The browser is not on the Docker network, so `VITE_API_BASE_URL` must be the **host** URL (`http://localhost:8000`), never `http://api:8000`.

The API key lives in `sessionStorage` (tab-scoped). `localStorage` would persist across sessions and is easier to leak in screenshots. Health and ready do not require auth; sending `Authorization: Bearer` anyway keeps one fetch helper.

Empty workspace is intentional: collections are UI-01.
