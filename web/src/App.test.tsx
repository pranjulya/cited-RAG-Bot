import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import { API_KEY_STORAGE_KEY } from "./auth";

function jsonResponse(body: unknown, ok = true): Response {
  return {
    ok,
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
      throw new Error(`unexpected ${url}`);
    }),
  );
  sessionStorage.setItem(API_KEY_STORAGE_KEY, "replace-me");
  render(<App />);
  await screen.findByLabelText("API status");
  expect(screen.getByText("failed")).toBeInTheDocument();
  expect(screen.getByText("Create a collection in the next phase.")).toBeInTheDocument();
});
