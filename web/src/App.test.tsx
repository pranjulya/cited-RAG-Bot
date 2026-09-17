import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import { API_KEY_STORAGE_KEY } from "./auth";

function jsonResponse(body: unknown, ok = true, status = ok ? 200 : 503): Response {
  return {
    ok,
    status,
    json: async () => body,
  } as Response;
}

test("key gate rejects an empty key", async () => {
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: "Connect" }));
  expect(screen.getByText("API key is required")).toBeInTheDocument();
  expect(sessionStorage.getItem(API_KEY_STORAGE_KEY)).toBeNull();
  expect(screen.queryByLabelText("API status")).not.toBeInTheDocument();
});

test("stores the key in sessionStorage and sends Authorization Bearer", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/health") || url.endsWith("/ready")) {
      expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer replace-me");
      return jsonResponse({ status: "ok" });
    }
    if (url.endsWith("/v1/collections")) {
      return jsonResponse([]);
    }
    throw new Error(`unexpected ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);
  await user.type(screen.getByLabelText("API key"), "replace-me");
  await user.click(screen.getByRole("button", { name: "Connect" }));

  expect(sessionStorage.getItem(API_KEY_STORAGE_KEY)).toBe("replace-me");
  expect(localStorage.getItem(API_KEY_STORAGE_KEY)).toBeNull();

  await screen.findByLabelText("API status");
  expect(screen.getAllByText("ok")).toHaveLength(2);
  expect(fetchMock).toHaveBeenCalled();
  const urls = fetchMock.mock.calls.map((call) => String(call[0]));
  expect(urls.some((url) => url.endsWith("/health"))).toBe(true);
  expect(urls.some((url) => url.endsWith("/ready"))).toBe(true);
});

test("ready 503 is a failed badge, not a blank screen", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/health")) {
        return jsonResponse({ status: "ok" });
      }
      if (url.endsWith("/ready")) {
        return jsonResponse({ status: "error" }, false);
      }
      if (url.endsWith("/v1/collections")) {
        return jsonResponse([]);
      }
      throw new Error(`unexpected ${url}`);
    }),
  );
  sessionStorage.setItem(API_KEY_STORAGE_KEY, "replace-me");
  render(<App />);
  await screen.findByLabelText("API status");
  expect(screen.getByText("failed")).toBeInTheDocument();
  expect(screen.getByText("No collections yet.")).toBeInTheDocument();
});

test("creates a collection and opens its shell without UUID entry", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/health") || url.endsWith("/ready")) {
        return jsonResponse({ status: "ok" });
      }
      if (url.endsWith("/v1/collections") && init?.method === "POST") {
        return jsonResponse({
          collection_id: "11111111-1111-1111-1111-111111111111",
          name: "Acme HR policies",
          status: "ACTIVE",
        });
      }
      if (url.endsWith("/v1/collections")) {
        return jsonResponse([]);
      }
      throw new Error(`unexpected ${url}`);
    }),
  );
  sessionStorage.setItem(API_KEY_STORAGE_KEY, "replace-me");
  const user = userEvent.setup();
  render(<App />);

  await screen.findByText("No collections yet.");
  await user.type(screen.getByLabelText("Collection name"), "Acme HR policies");
  await user.click(screen.getByRole("button", { name: "Create collection" }));
  await user.click(await screen.findByRole("link", { name: "Acme HR policies" }));

  expect(window.location.pathname).toBe("/collections/11111111-1111-1111-1111-111111111111");
  expect(screen.getByRole("heading", { name: "Acme HR policies" })).toBeInTheDocument();
  expect(screen.getByText("Documents arrive in the next phase.")).toBeInTheDocument();
});

test("shows an inline error for a blank collection name", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => jsonResponse([])),
  );
  sessionStorage.setItem(API_KEY_STORAGE_KEY, "replace-me");
  const user = userEvent.setup();
  render(<App />);

  await screen.findByText("No collections yet.");
  await user.click(screen.getByRole("button", { name: "Create collection" }));

  expect(screen.getByText("Collection name is required")).toBeInTheDocument();
});

test("returns to the key gate when the collection list is unauthorized", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/health") || url.endsWith("/ready")) {
        return jsonResponse({ status: "ok" });
      }
      if (url.endsWith("/v1/collections")) {
        return jsonResponse({ detail: "unauthorized" }, false, 401);
      }
      throw new Error(`unexpected ${url}`);
    }),
  );
  sessionStorage.setItem(API_KEY_STORAGE_KEY, "expired");
  render(<App />);

  expect(await screen.findByLabelText("API key")).toBeInTheDocument();
  expect(sessionStorage.getItem(API_KEY_STORAGE_KEY)).toBeNull();
});
