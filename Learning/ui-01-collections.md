# UI-01 — Collections

The console needs an index endpoint because a create-only API leaves people copying UUIDs from responses. `GET /v1/collections` is still principal-scoped: the repository filters by `owner_id`, and the browser only talks to FastAPI with the existing Bearer key.

The collection ID belongs in a clicked URL, not a form field. The empty, unavailable, and unauthorized states remain distinct: an empty list is normal, an unavailable list can retry, and a 401 clears the tab-scoped key and returns to the gate.
