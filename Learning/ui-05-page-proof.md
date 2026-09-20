# UI-05 — Page Proof

The console now fetches source PDFs through the authenticated API rather than
using a public bucket URL. The route authorizes the document's collection,
selects the active version (or the newest stored version), reads the canonical
source key, and returns raw `application/pdf` bytes with `private, no-store`.
Missing or unauthorized documents deliberately share a 404 response, while a
missing object is a 503 and an oversized object is a 413.

Citation page numbers are already parser-owned, 1-based values. The browser
keeps that authority: it turns the authenticated response into a blob URL and
passes `#page=<page_start>` to the native PDF viewer. No raster page endpoint,
public URL, client-side page-number repair, or extra viewer dependency is
needed.
