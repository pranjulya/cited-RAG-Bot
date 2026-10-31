import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { API_KEY_STORAGE_KEY } from "../auth";
import { ChatApp, matchEvidence } from "./ChatApp";
import type { Evidence, QueryResponse } from "./types";

const COLLECTION = { collection_id: "c1", name: "HR policies", status: "ACTIVE" };
const DOC = "d1";
const VERSION = "v1";
const READY_DOC = { document_id: DOC, logical_name: "handbook.pdf", status: "READY", document_version_id: VERSION };

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    blob: async () => new Blob(["%PDF"], { type: "application/pdf" }),
  } as Response;
}

function evidence(overrides: Partial<Evidence> = {}): Evidence {
  return {
    id: "E1",
    document_id: DOC,
    document_version_id: VERSION,
    document_name: "handbook.pdf",
    page_start: 3,
    page_end: 3,
    text: "Expense claims must be submitted within 30 days.",
    truncated: false,
    ...overrides,
  };
}

function answered(overrides: Partial<QueryResponse> = {}): QueryResponse {
  return {
    request_id: "r1",
    status: "ANSWERED",
    answer: "Expense claims must be submitted within 30 days.",
    citations: [
      { document_id: DOC, document_version_id: VERSION, document_name: "handbook.pdf", page_start: 3, page_end: 3 },
    ],
    reason: null,
    trace: {
      correlation_id: "corr",
      evidence: [
        evidence(),
        evidence({ id: "E2", document_id: "other-doc", text: "A different file with the same name." }),
      ],
    },
    ...overrides,
  };
}

type Handler = (url: string, init?: RequestInit) => Response | undefined;

function stubApi(handler: Handler, documents: unknown[] = [READY_DOC]) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const custom = handler(url, init);
    if (custom) return custom;
    if (url.endsWith("/v1/collections") && (!init?.method || init.method === "GET")) {
      return jsonResponse([COLLECTION]);
    }
    if (url.endsWith("/v1/collections/c1/documents") && (!init?.method || init.method === "GET")) {
      return jsonResponse(documents);
    }
    throw new Error(`unexpected ${init?.method ?? "GET"} ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function connectedAt(path = "/chat") {
  sessionStorage.setItem(API_KEY_STORAGE_KEY, "replace-me");
  window.history.replaceState({}, "", path);
}

async function askQuestion(text: string) {
  const user = userEvent.setup();
  const input = await screen.findByLabelText("Your question");
  await waitFor(() => expect(input).toBeEnabled());
  await user.type(input, text);
  await user.click(screen.getByRole("button", { name: "Send" }));
  return user;
}

test("gate requires a key and stores it only in sessionStorage", async () => {
  stubApi(() => undefined);
  const user = userEvent.setup();
  window.history.replaceState({}, "", "/chat");
  render(<ChatApp />);
  await user.click(screen.getByRole("button", { name: "Continue" }));
  expect(screen.getByRole("alert")).toHaveTextContent("Enter your access key.");

  await user.type(screen.getByLabelText("Access key"), "replace-me");
  await user.click(screen.getByRole("button", { name: "Continue" }));
  expect(sessionStorage.getItem(API_KEY_STORAGE_KEY)).toBe("replace-me");
  expect(localStorage.getItem(API_KEY_STORAGE_KEY)).toBeNull();
  expect(await screen.findByRole("combobox", { name: "Choose knowledge base" })).toHaveValue("c1");
  expect(window.location.pathname).toBe("/chat/c1");
});

test("a 401 signs the user out", async () => {
  stubApi((url) => (url.endsWith("/v1/collections") ? jsonResponse({ detail: "unauthorized" }, 401) : undefined));
  connectedAt();
  render(<ChatApp />);
  expect(await screen.findByLabelText("Access key")).toBeInTheDocument();
  expect(sessionStorage.getItem(API_KEY_STORAGE_KEY)).toBeNull();
});

test("input stays disabled until a document is ready, then upload polls to Ready", async () => {
  let polls = 0;
  stubApi((url, init) => {
    if (url.endsWith("/v1/collections/c1/documents") && init?.method === "POST") {
      return jsonResponse({ document_id: "d9", document_version_id: "v9", status: "QUEUED" }, 202);
    }
    if (url.endsWith("/v1/documents/d9")) {
      polls += 1;
      return jsonResponse({ document_id: "d9", logical_name: "policy.pdf", status: "READY" });
    }
    return undefined;
  }, []);
  connectedAt("/chat/c1");
  const user = userEvent.setup();
  render(<ChatApp />);

  const input = await screen.findByLabelText("Your question");
  expect(input).toBeDisabled();
  await user.upload(screen.getByLabelText("Add PDF files"), new File(["%PDF"], "policy.pdf", { type: "application/pdf" }));

  await waitFor(() => expect(screen.getByText("Ready")).toBeInTheDocument());
  expect(polls).toBe(1);
  expect(input).toBeEnabled();
});

test("an upload that finishes before the document list loads is not dropped", async () => {
  let releaseList: (response: Response) => void = () => undefined;
  const slowList = new Promise<Response>((resolve) => {
    releaseList = resolve;
  });
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/v1/collections")) return jsonResponse([COLLECTION]);
    if (url.endsWith("/v1/collections/c1/documents") && init?.method === "POST") {
      return jsonResponse({ document_id: "d9", status: "QUEUED" }, 202);
    }
    if (url.endsWith("/v1/collections/c1/documents")) return slowList;
    if (url.endsWith("/v1/documents/d9")) return jsonResponse({ document_id: "d9", logical_name: "new.pdf", status: "READY" });
    throw new Error(`unexpected ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  connectedAt("/chat/c1");
  const user = userEvent.setup();
  render(<ChatApp />);

  await screen.findByRole("button", { name: "Add PDF" });
  await user.upload(screen.getByLabelText("Add PDF files"), new File(["%PDF"], "new.pdf", { type: "application/pdf" }));
  releaseList(jsonResponse([READY_DOC]));

  expect(await screen.findByText("handbook.pdf")).toBeInTheDocument();
  expect(screen.getByText("new.pdf")).toBeInTheDocument();
});

test("non-PDF files are rejected before upload", async () => {
  const fetchMock = stubApi(() => undefined);
  connectedAt("/chat/c1");
  const user = userEvent.setup({ applyAccept: false });
  render(<ChatApp />);
  await screen.findByText("handbook.pdf");
  await user.upload(screen.getByLabelText("Add PDF files"), new File(["x"], "notes.txt", { type: "text/plain" }));
  expect(screen.getByRole("alert")).toHaveTextContent("notes.txt is not a PDF.");
  expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);
});

test("failed documents show a plain-language reason", async () => {
  stubApi(() => undefined, [
    { document_id: "d2", logical_name: "scan.pdf", status: "FAILED", failure_code: "PDF_UNSUPPORTED" },
  ]);
  connectedAt("/chat/c1");
  render(<ChatApp />);
  expect(await screen.findByText("Failed")).toBeInTheDocument();
  expect(screen.getByText("No selectable text. Scanned PDFs are not supported.")).toBeInTheDocument();
});

test("answer shows numbered sources; opening one shows only evidence from that document version", async () => {
  stubApi((url) => {
    if (url.endsWith("/v1/collections/c1/query")) return jsonResponse(answered());
    if (url.endsWith(`/v1/documents/${DOC}/content`)) return jsonResponse({});
    return undefined;
  });
  URL.createObjectURL = vi.fn(() => "blob:pdf");
  URL.revokeObjectURL = vi.fn();
  connectedAt("/chat/c1");
  render(<ChatApp />);
  const user = await askQuestion("How long do I have for expenses?");

  const thread = screen.getByRole("region", { name: "Conversation" });
  expect(await within(thread).findByText("Expense claims must be submitted within 30 days.")).toBeInTheDocument();
  expect(within(thread).getByText("How long do I have for expenses?")).toBeInTheDocument();
  await user.click(within(thread).getByRole("button", { name: "Source 1: handbook.pdf, page 3" }));

  const viewer = await screen.findByRole("complementary", { name: "Source viewer" });
  const quoted = within(viewer).getByRole("region", { name: "Quoted passage" });
  expect(quoted).toHaveTextContent("Expense claims must be submitted within 30 days.");
  expect(quoted).not.toHaveTextContent("A different file with the same name.");
  expect(await within(viewer).findByTitle("handbook.pdf page 3")).toHaveAttribute("src", "blob:pdf#page=3");
});

test("insufficient evidence, 503, and blocked citations are three different messages", async () => {
  const replies = [
    jsonResponse(answered({ status: "INSUFFICIENT_EVIDENCE", answer: "", citations: [], reason: "MODEL_ABSTENTION" })),
    jsonResponse({ detail: "DENSE_RETRIEVAL_ERROR" }, 503),
    jsonResponse({ detail: "citation_validation_failed" }, 422),
  ];
  stubApi((url) => (url.endsWith("/v1/collections/c1/query") ? replies.shift() : undefined));
  connectedAt("/chat/c1");
  render(<ChatApp />);

  await askQuestion("dress code?");
  expect(await screen.findByText("Your documents don't contain a clear answer to this.")).toBeInTheDocument();
  expect(screen.getByText("Reason code: MODEL_ABSTENTION")).toBeInTheDocument();

  await askQuestion("leave?");
  expect(
    await screen.findByText("The answer service is temporarily unavailable. Nothing was answered."),
  ).toBeInTheDocument();
  expect(screen.getByText("Failure code: DENSE_RETRIEVAL_ERROR")).toBeInTheDocument();

  await askQuestion("remote?");
  expect(
    await screen.findByText("An answer was produced, but its sources could not be verified, so it was blocked."),
  ).toBeInTheDocument();
});

test("retry re-asks the same question in place", async () => {
  const replies = [jsonResponse({ detail: "RERANKER_ERROR" }, 503), jsonResponse(answered())];
  stubApi((url) => (url.endsWith("/v1/collections/c1/query") ? replies.shift() : undefined));
  connectedAt("/chat/c1");
  render(<ChatApp />);
  const user = await askQuestion("expenses?");
  await user.click(await screen.findByRole("button", { name: "Try again" }));
  expect(await screen.findByText("Expense claims must be submitted within 30 days.")).toBeInTheDocument();
  expect(screen.getAllByText("expenses?")).toHaveLength(1);
});

test("only the current question is sent and the thread is not stored in the browser", async () => {
  const bodies: string[] = [];
  stubApi((url, init) => {
    if (url.endsWith("/v1/collections/c1/query")) {
      bodies.push(String(init?.body));
      return jsonResponse(answered());
    }
    return undefined;
  });
  connectedAt("/chat/c1");
  render(<ChatApp />);
  await askQuestion("first question");
  await screen.findByText("Expense claims must be submitted within 30 days.");
  await askQuestion("second question");
  await waitFor(() => expect(bodies).toHaveLength(2));

  expect(JSON.parse(bodies[1])).toEqual({ question: "second question" });
  const stored = JSON.stringify({ ...sessionStorage }) + JSON.stringify({ ...localStorage });
  expect(stored).not.toContain("first question");
  expect(stored).not.toContain("30 days");
});

test("answer and evidence text render as text, not HTML", async () => {
  const hostile = '<img src=x onerror="alert(1)">';
  stubApi((url) => (url.endsWith("/v1/collections/c1/query") ? jsonResponse(answered({ answer: hostile })) : undefined));
  connectedAt("/chat/c1");
  const { container } = render(<ChatApp />);
  await askQuestion("anything");
  expect(await screen.findByText(hostile)).toBeInTheDocument();
  expect(container.querySelector("img")).toBeNull();
});

test("matchEvidence requires the same document version and an overlapping page", () => {
  const citation = { document_id: DOC, document_version_id: VERSION, document_name: "handbook.pdf", page_start: 2, page_end: 3 };
  const items = [
    evidence({ id: "E1", page_start: 3, page_end: 4 }),
    evidence({ id: "E2", page_start: 5, page_end: 5 }),
    evidence({ id: "E3", document_version_id: "old" }),
    evidence({ id: "E4", document_id: "other", document_name: "handbook.pdf" }),
  ];
  expect(matchEvidence(citation, items).map((item) => item.id)).toEqual(["E1"]);
});
