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
  expect(screen.getByLabelText("Upload PDF")).toBeInTheDocument();
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

test("uploads a PDF and stops polling when it is ready", async () => {
  const collectionId = "11111111-1111-1111-1111-111111111111";
  const documentId = "22222222-2222-2222-2222-222222222222";
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/health") || url.endsWith("/ready")) return jsonResponse({ status: "ok" });
      if (url.endsWith("/v1/collections")) {
        return jsonResponse([{ collection_id: collectionId, name: "Acme HR", status: "ACTIVE" }]);
      }
      if (url.endsWith(`/v1/collections/${collectionId}/documents`) && init?.method === "POST") {
        return jsonResponse({ document_id: documentId, document_version_id: documentId, status: "QUEUED" });
      }
      if (url.endsWith(`/v1/collections/${collectionId}/documents`)) return jsonResponse([]);
      if (url.endsWith(`/v1/documents/${documentId}`)) {
        return jsonResponse({ document_id: documentId, logical_name: "policy.pdf", status: "READY" });
      }
      throw new Error(`unexpected ${url}`);
    });
  vi.stubGlobal("fetch", fetchMock);
  window.history.replaceState({}, "", `/collections/${collectionId}`);
  sessionStorage.setItem(API_KEY_STORAGE_KEY, "replace-me");
  const user = userEvent.setup();
  render(<App />);

  await screen.findByRole("heading", { name: "Acme HR" });
  await user.upload(screen.getByLabelText("Upload PDF"), new File(["pdf"], "policy.pdf", { type: "application/pdf" }));
  await user.click(screen.getByRole("button", { name: "Upload" }));

  expect(await screen.findByText("READY")).toBeInTheDocument();
  expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith(`/v1/documents/${documentId}`))).toHaveLength(1);
});

test("shows a failed document and its failure code", async () => {
  const collectionId = "11111111-1111-1111-1111-111111111111";
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/health") || url.endsWith("/ready")) return jsonResponse({ status: "ok" });
      if (url.endsWith("/v1/collections")) {
        return jsonResponse([{ collection_id: collectionId, name: "Acme HR", status: "ACTIVE" }]);
      }
      if (url.endsWith(`/v1/collections/${collectionId}/documents`)) {
        return jsonResponse([{ document_id: "doc", logical_name: "scan.pdf", status: "FAILED", version_number: 1, failure_code: "PDF_UNSUPPORTED" }]);
      }
      throw new Error(`unexpected ${url}`);
    }),
  );
  window.history.replaceState({}, "", `/collections/${collectionId}`);
  sessionStorage.setItem(API_KEY_STORAGE_KEY, "replace-me");
  render(<App />);

  expect(await screen.findByText(/\(PDF_UNSUPPORTED\)/)).toBeInTheDocument();
  expect(screen.getByText("FAILED")).toBeInTheDocument();
  expect(screen.getByText("1")).toBeInTheDocument();
});

function stubQueryApp(queryResponse: unknown, ok = true, status = 200) {
  const collectionId = "11111111-1111-1111-1111-111111111111";
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/health") || url.endsWith("/ready")) return jsonResponse({ status: "ok" });
    if (url.endsWith("/v1/collections")) {
      return jsonResponse([{ collection_id: collectionId, name: "Acme HR", status: "ACTIVE" }]);
    }
    if (url.endsWith(`/v1/collections/${collectionId}/documents`)) return jsonResponse([]);
    if (url.endsWith(`/v1/collections/${collectionId}/query`)) return jsonResponse(queryResponse, ok, status);
    throw new Error(`unexpected ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  window.history.replaceState({}, "", `/collections/${collectionId}`);
  sessionStorage.setItem(API_KEY_STORAGE_KEY, "replace-me");
  return fetchMock;
}

async function openQueryPanel() {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { name: "Acme HR" });
  return user;
}

test("renders an answered query with page citation and request id", async () => {
  const requestId = "33333333-3333-3333-3333-333333333333";
  const fetchMock = stubQueryApp({
    request_id: requestId,
    status: "ANSWERED",
    answer: "Employees receive 20 days of leave.",
    citations: [{
      document_id: "doc",
      document_version_id: "version",
      document_name: "handbook.pdf",
      page_start: 1,
      page_end: 2,
    }],
    reason: null,
  });
  const user = await openQueryPanel();
  await user.type(screen.getByLabelText("Question"), "How much leave?");
  await user.click(screen.getByRole("button", { name: "Ask" }));

  expect(await screen.findByText("Employees receive 20 days of leave.")).toBeInTheDocument();
  expect(screen.getByText("handbook.pdf · pages 1–2")).toBeInTheDocument();
  expect(screen.getByText(`Request ${requestId}`)).toBeInTheDocument();
  expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith(`/v1/collections/11111111-1111-1111-1111-111111111111/query`))).toBe(true);
});

test("renders insufficient evidence without an answer", async () => {
  stubQueryApp({
    request_id: "33333333-3333-3333-3333-333333333333",
    status: "INSUFFICIENT_EVIDENCE",
    answer: "",
    citations: [],
    reason: "NO_RETRIEVAL_RESULTS",
  });
  const user = await openQueryPanel();
  await user.type(screen.getByLabelText("Question"), "Who leads OpenAI?");
  await user.click(screen.getByRole("button", { name: "Ask" }));

  expect(await screen.findByText("Insufficient evidence")).toBeInTheDocument();
  expect(screen.getByText("Reason: NO_RETRIEVAL_RESULTS")).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Answer" })).not.toBeInTheDocument();
});

test("renders a query outage separately from abstention", async () => {
  stubQueryApp({ detail: "query_failed" }, false, 503);
  const user = await openQueryPanel();
  await user.type(screen.getByLabelText("Question"), "How much leave?");
  await user.click(screen.getByRole("button", { name: "Ask" }));

  expect(await screen.findByText("Query service unavailable. Try again later.")).toBeInTheDocument();
  expect(screen.queryByText("Insufficient evidence")).not.toBeInTheDocument();
});

test("keeps empty questions disabled and displays a 413 query error", async () => {
  stubQueryApp({ detail: "query_too_long" }, false, 413);
  const user = await openQueryPanel();
  const ask = screen.getByRole("button", { name: "Ask" });
  expect(ask).toBeDisabled();
  await user.type(screen.getByLabelText("Question"), "A question");
  expect(ask).toBeEnabled();
  await user.click(ask);

  expect(await screen.findByText("Question is too long.")).toBeInTheDocument();
});
