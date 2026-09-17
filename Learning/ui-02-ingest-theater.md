# UI-02 — Ingest Theater

`202 Accepted` means the API stored a PDF and queued work; it does not mean the document is searchable. The console therefore displays `QUEUED` immediately and polls the authenticated document-status endpoint until the worker reports `READY` or `FAILED`.

`READY` is deliberately late: the ingest worker must finish both dense and sparse indexing first. A scanned PDF can instead become `FAILED` with `PDF_UNSUPPORTED`; the console shows that public code but never exposes PDF text. Polling is the small V1 choice here; a later realtime channel can replace the timer without weakening the status contract.
