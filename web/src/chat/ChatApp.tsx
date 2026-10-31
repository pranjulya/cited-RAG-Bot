import { ChangeEvent, FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { apiFetch } from "../api";
import { clearApiKey, getApiKey, setApiKey } from "../auth";
import type { ChatDocument, Citation, Collection, Evidence, QueryResponse, SourceView, Turn } from "./types";
import "./chat.css";

const POLL_LIMIT = 60;

const NO_ANSWER_TEXT: Record<string, { headline: string; detail: string }> = {
  NO_READY_DOCUMENTS: {
    headline: "There are no ready documents yet.",
    detail: "Add a PDF and wait until it shows Ready, then ask again.",
  },
  NO_RETRIEVAL_RESULTS: {
    headline: "I couldn't find anything about this in your documents.",
    detail: "Try different words, or add the document that covers this topic.",
  },
  CONTEXT_EMPTY: {
    headline: "I couldn't find anything about this in your documents.",
    detail: "Try different words, or add the document that covers this topic.",
  },
  WEAK_EVIDENCE: {
    headline: "I found related passages, but they don't clearly answer this.",
    detail: "I only answer when your documents support the answer, so I won't guess.",
  },
  MODEL_ABSTENTION: {
    headline: "Your documents don't contain a clear answer to this.",
    detail: "I only answer when your documents support the answer, so I won't guess.",
  },
};

const FAILURE_TEXT: Record<string, string> = {
  PDF_UNSUPPORTED: "No selectable text. Scanned PDFs are not supported.",
  PDF_PASSWORD_PROTECTED: "This PDF is password-protected.",
  PDF_PARSE_FAILED: "This PDF could not be read.",
};

function collectionIdFromPath(): string | null {
  return window.location.pathname.match(/^\/chat\/([^/]+)$/)?.[1] ?? null;
}

function pageLabel(item: { page_start: number; page_end: number }): string {
  return item.page_start === item.page_end
    ? `page ${item.page_start}`
    : `pages ${item.page_start}–${item.page_end}`;
}

function statusView(status: string | null): { label: string; tone: string } {
  if (status === "READY") return { label: "Ready", tone: "ok" };
  if (status === "FAILED") return { label: "Failed", tone: "bad" };
  if (status === "DELETING" || status === "DELETED") return { label: "Removing", tone: "muted" };
  return { label: "Processing", tone: "busy" };
}

/** Evidence for a citation: same document version and an overlapping page range. Never by file name. */
export function matchEvidence(citation: Citation, evidence: Evidence[]): Evidence[] {
  return evidence.filter(
    (item) =>
      item.document_id === citation.document_id &&
      item.document_version_id === citation.document_version_id &&
      item.page_start <= citation.page_end &&
      item.page_end >= citation.page_start,
  );
}

type QueryFailure = { message: string; code: string | null; retryable: boolean };

function queryError(status: number, detail: string | undefined): QueryFailure {
  if (status === 503) {
    return {
      message: "The answer service is temporarily unavailable. Nothing was answered.",
      code: detail ?? null,
      retryable: true,
    };
  }
  if (status === 422 && detail === "citation_validation_failed") {
    return {
      message: "An answer was produced, but its sources could not be verified, so it was blocked.",
      code: detail,
      retryable: true,
    };
  }
  if (status === 413) return { message: "This question is too long. Please shorten it.", code: null, retryable: false };
  if (status === 404) return { message: "This knowledge base no longer exists.", code: null, retryable: false };
  return { message: "This question could not be answered.", code: detail ?? null, retryable: true };
}

export function ChatApp() {
  const [connected, setConnected] = useState(() => Boolean(getApiKey()));
  const [keyInput, setKeyInput] = useState("");
  const [gateError, setGateError] = useState<string | null>(null);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [collectionsLoaded, setCollectionsLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(collectionIdFromPath);
  const [newName, setNewName] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<ChatDocument[]>([]);
  const [docError, setDocError] = useState<string | null>(null);
  const [threads, setThreads] = useState<Record<string, Turn[]>>({});
  const [question, setQuestion] = useState("");
  const [source, setSource] = useState<SourceView | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const activeRef = useRef(activeId);
  const sourceUrlRef = useRef<string | null>(null);
  const sourceRequestRef = useRef(0);
  const turnCounter = useRef(0);
  const threadEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const active = collections.find((collection) => collection.collection_id === activeId) ?? null;
  const turns = (activeId && threads[activeId]) || [];
  const readyCount = documents.filter((document) => document.status === "READY").length;
  const asking = turns.some((turn) => turn.state === "pending");

  useEffect(() => {
    document.title = "Cited — Ask your documents";
  }, []);

  function signOut() {
    clearApiKey();
    setConnected(false);
    setCollections([]);
    setCollectionsLoaded(false);
    setDocuments([]);
    setThreads({});
    closeSource();
  }

  function closeSource() {
    sourceRequestRef.current += 1;
    if (sourceUrlRef.current) {
      URL.revokeObjectURL(sourceUrlRef.current);
      sourceUrlRef.current = null;
    }
    setSource(null);
  }

  function selectCollection(collectionId: string | null, replace = false) {
    const path = collectionId ? `/chat/${collectionId}` : "/chat";
    if (window.location.pathname !== path) {
      if (replace) window.history.replaceState({}, "", path);
      else window.history.pushState({}, "", path);
    }
    activeRef.current = collectionId;
    setActiveId(collectionId);
    setDrawerOpen(false);
  }

  useEffect(() => {
    if (!connected) return;
    let cancelled = false;
    void apiFetch("/v1/collections")
      .then(async (response) => {
        if (cancelled) return;
        if (response.status === 401) {
          signOut();
          return;
        }
        if (!response.ok) throw new Error("collections_unavailable");
        setCollections((await response.json()) as Collection[]);
        setCollectionsLoaded(true);
        setLoadError(null);
      })
      .catch(() => !cancelled && setLoadError("Your knowledge bases could not be loaded. Try again shortly."));
    return () => {
      cancelled = true;
    };
  }, [connected]);

  useEffect(() => {
    if (!collectionsLoaded) return;
    if (activeId && collections.some((collection) => collection.collection_id === activeId)) return;
    selectCollection(collections[0]?.collection_id ?? null, true);
  }, [collectionsLoaded, collections, activeId]);

  useEffect(() => {
    function onPopState() {
      selectCollection(collectionIdFromPath());
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    closeSource();
    setDocuments([]);
    setDocError(null);
    if (!connected || !activeId) return;
    const collectionId = activeId;
    let cancelled = false;
    void apiFetch(`/v1/collections/${collectionId}/documents`)
      .then(async (response) => {
        if (!response.ok) throw new Error("documents_unavailable");
        const loaded = (await response.json()) as ChatDocument[];
        if (cancelled) return;
        // Keep rows added by an upload that finished before this list arrived.
        setDocuments((current) => [
          ...loaded,
          ...current.filter((item) => !loaded.some((document) => document.document_id === item.document_id)),
        ]);
        for (const document of loaded) {
          if (document.status !== "READY" && document.status !== "FAILED") {
            void pollDocument(document.document_id, collectionId);
          }
        }
      })
      .catch(() => !cancelled && setDocError("Documents could not be loaded."));
    return () => {
      cancelled = true;
    };
  }, [connected, activeId]);

  useEffect(() => () => {
    if (sourceUrlRef.current) URL.revokeObjectURL(sourceUrlRef.current);
  }, []);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView?.({ block: "end" });
  }, [turns.length, turns[turns.length - 1]?.state]);

  function onConnect(event: FormEvent) {
    event.preventDefault();
    const trimmed = keyInput.trim();
    if (!trimmed) {
      setGateError("Enter your access key.");
      return;
    }
    setApiKey(trimmed);
    setKeyInput("");
    setGateError(null);
    setConnected(true);
  }

  async function onCreateCollection(event: FormEvent) {
    event.preventDefault();
    const name = newName.trim();
    if (!name) {
      setNameError("Enter a name.");
      return;
    }
    try {
      const response = await apiFetch("/v1/collections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (response.status === 401) {
        signOut();
        return;
      }
      if (!response.ok) throw new Error("create_failed");
      const created = (await response.json()) as Collection;
      setCollections((current) => [...current, created]);
      setNewName("");
      setNameError(null);
      selectCollection(created.collection_id);
    } catch {
      setNameError("The knowledge base could not be created.");
    }
  }

  async function pollDocument(documentId: string, collectionId: string, attempt = 0): Promise<void> {
    if (activeRef.current !== collectionId) return;
    let response: Response;
    try {
      response = await apiFetch(`/v1/documents/${documentId}`);
    } catch {
      response = { ok: false, status: 0 } as Response;
    }
    if (activeRef.current !== collectionId) return;
    if (response.status === 404) {
      setDocuments((current) => current.filter((document) => document.document_id !== documentId));
      return;
    }
    if (response.ok) {
      const loaded = (await response.json()) as ChatDocument;
      if (activeRef.current !== collectionId) return;
      setDocuments((current) =>
        current.map((document) => (document.document_id === documentId ? loaded : document)),
      );
      if (loaded.status === "READY" || loaded.status === "FAILED") return;
    }
    if (attempt >= POLL_LIMIT) {
      setDocError("A document is taking longer than expected. Check again shortly.");
      return;
    }
    window.setTimeout(() => void pollDocument(documentId, collectionId, attempt + 1), 1000);
  }

  async function uploadFile(file: File, collectionId: string) {
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setDocError(`${file.name} is not a PDF.`);
      return;
    }
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await apiFetch(`/v1/collections/${collectionId}/documents`, { method: "POST", body });
      if (response.status === 401) {
        signOut();
        return;
      }
      if (!response.ok) {
        const detail = ((await response.json().catch(() => ({}))) as { detail?: unknown }).detail;
        setDocError(
          typeof detail === "string" ? `${file.name} could not be added: ${detail}.` : `${file.name} could not be added.`,
        );
        return;
      }
      const uploaded = (await response.json()) as { document_id: string; status: string };
      if (activeRef.current !== collectionId) return;
      setDocuments((current) => [
        ...current.filter((document) => document.document_id !== uploaded.document_id),
        { document_id: uploaded.document_id, logical_name: file.name, status: uploaded.status },
      ]);
      void pollDocument(uploaded.document_id, collectionId);
    } catch {
      setDocError(`${file.name} could not be added. Try again shortly.`);
    }
  }

  async function onFilesChosen(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (!activeId) return;
    setDocError(null);
    for (const file of files) await uploadFile(file, activeId);
  }

  async function onRemoveDocument(target: ChatDocument) {
    if (!activeId || !window.confirm(`Remove ${target.logical_name}? Questions will no longer use it.`)) return;
    const collectionId = activeId;
    setDocError(null);
    try {
      const response = await apiFetch(`/v1/documents/${target.document_id}`, { method: "DELETE" });
      if (response.status === 401) {
        signOut();
        return;
      }
      if (!response.ok) throw new Error("delete_failed");
      setDocuments((current) =>
        current.map((document) =>
          document.document_id === target.document_id ? { ...document, status: "DELETING" } : document,
        ),
      );
      void pollDocument(target.document_id, collectionId);
    } catch {
      setDocError(`${target.logical_name} could not be removed.`);
    }
  }

  async function ask(text: string, existingId?: string) {
    const collectionId = activeId;
    if (!collectionId) return;
    const id = existingId ?? `turn-${++turnCounter.current}`;
    const update = (turn: Turn) =>
      setThreads((current) => {
        const thread = current[collectionId] ?? [];
        const next = thread.some((item) => item.id === id)
          ? thread.map((item) => (item.id === id ? turn : item))
          : [...thread, turn];
        return { ...current, [collectionId]: next };
      });
    update({ id, question: text, state: "pending" });
    try {
      const response = await apiFetch(`/v1/collections/${collectionId}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text }),
      });
      if (response.status === 401) {
        signOut();
        return;
      }
      if (!response.ok) {
        const detail = ((await response.json().catch(() => ({}))) as { detail?: unknown }).detail;
        update({ id, question: text, state: "error", ...queryError(response.status, typeof detail === "string" ? detail : undefined) });
        return;
      }
      update({ id, question: text, state: "done", response: (await response.json()) as QueryResponse });
    } catch {
      update({
        id,
        question: text,
        state: "error",
        message: "The answer service can't be reached. Nothing was answered.",
        code: null,
        retryable: true,
      });
    }
  }

  function onSend(event?: FormEvent) {
    event?.preventDefault();
    const text = question.trim();
    if (!text || asking || readyCount === 0) return;
    setQuestion("");
    void ask(text);
  }

  function onComposerKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      onSend();
    }
  }

  async function openSource(citation: Citation, index: number, evidence: Evidence[]) {
    const requestId = ++sourceRequestRef.current;
    if (sourceUrlRef.current) {
      URL.revokeObjectURL(sourceUrlRef.current);
      sourceUrlRef.current = null;
    }
    setSource({ citation, index, evidence: matchEvidence(citation, evidence), url: null, error: null });
    try {
      const response = await apiFetch(`/v1/documents/${citation.document_id}/content`);
      if (requestId !== sourceRequestRef.current) return;
      if (!response.ok) throw new Error("content_unavailable");
      const url = URL.createObjectURL(await response.blob());
      if (requestId !== sourceRequestRef.current) {
        URL.revokeObjectURL(url);
        return;
      }
      sourceUrlRef.current = url;
      setSource((current) => (current ? { ...current, url } : current));
    } catch {
      if (requestId === sourceRequestRef.current) {
        setSource((current) => (current ? { ...current, error: "The source PDF is unavailable." } : current));
      }
    }
  }

  if (!connected) {
    return (
      <main className="chat-app chat-gate-wrap">
        <form className="chat-gate" onSubmit={onConnect}>
          <p className="chat-brand">Cited</p>
          <h1>Ask your HR documents</h1>
          <p className="chat-muted">
            Answers come only from the PDFs you upload, with the page each answer came from.
          </p>
          <label htmlFor="chat-key">Access key</label>
          <input
            id="chat-key"
            type="password"
            autoComplete="off"
            value={keyInput}
            onChange={(event) => setKeyInput(event.target.value)}
          />
          {gateError ? <p className="chat-error" role="alert">{gateError}</p> : null}
          <button type="submit" className="chat-primary">Continue</button>
        </form>
      </main>
    );
  }

  return (
    <div className="chat-app">
      <header className="chat-top">
        <button
          type="button"
          className="chat-drawer-toggle"
          aria-expanded={drawerOpen}
          aria-controls="chat-sidebar"
          onClick={() => setDrawerOpen((open) => !open)}
        >
          Documents ({readyCount} ready)
        </button>
        <p className="chat-brand">Cited</p>
        <span className="chat-top-title">{active?.name ?? ""}</span>
        <nav className="chat-top-links">
          <a href="/">Operator console</a>
          <button type="button" className="chat-link-button" onClick={signOut}>Sign out</button>
        </nav>
      </header>

      <div className="chat-body">
        <aside id="chat-sidebar" className="chat-sidebar" data-open={drawerOpen} aria-label="Knowledge base and documents">
          <section className="chat-panel">
            <h2>Knowledge base</h2>
            {collections.length > 0 ? (
              <select
                aria-label="Choose knowledge base"
                value={activeId ?? ""}
                onChange={(event) => selectCollection(event.target.value || null)}
              >
                {collections.map((collection) => (
                  <option key={collection.collection_id} value={collection.collection_id}>
                    {collection.name}
                  </option>
                ))}
              </select>
            ) : null}
            <form className="chat-new-kb" onSubmit={onCreateCollection}>
              <label htmlFor="kb-name">New knowledge base</label>
              <div className="chat-row">
                <input
                  id="kb-name"
                  placeholder="e.g. HR policies"
                  value={newName}
                  onChange={(event) => setNewName(event.target.value)}
                />
                <button type="submit">Create</button>
              </div>
              {nameError ? <p className="chat-error" role="alert">{nameError}</p> : null}
            </form>
          </section>

          {active ? (
            <section className="chat-panel">
              <div className="chat-panel-head">
                <h2>Documents</h2>
                <button type="button" className="chat-primary" onClick={() => fileInputRef.current?.click()}>
                  Add PDF
                </button>
              </div>
              <input
                ref={fileInputRef}
                className="visually-hidden"
                type="file"
                accept="application/pdf,.pdf"
                multiple
                aria-label="Add PDF files"
                onChange={(event) => void onFilesChosen(event)}
              />
              {docError ? <p className="chat-error" role="alert">{docError}</p> : null}
              {documents.length === 0 ? (
                <p className="chat-muted">No documents yet. Add a text PDF to get started.</p>
              ) : (
                <ul className="chat-docs">
                  {documents.map((document) => {
                    const view = statusView(document.status);
                    const failure = document.failure_code
                      ? FAILURE_TEXT[document.failure_code] ?? "This PDF could not be processed."
                      : null;
                    return (
                      <li key={document.document_id}>
                        <div className="chat-doc-line">
                          <span className="chat-doc-name" title={document.logical_name}>{document.logical_name}</span>
                          <span className="chat-status" data-tone={view.tone}>{view.label}</span>
                        </div>
                        {document.status === "FAILED" && failure ? <p className="chat-doc-fail">{failure}</p> : null}
                        {view.label !== "Removing" ? (
                          <button
                            type="button"
                            className="chat-link-button"
                            aria-label={`Remove ${document.logical_name}`}
                            onClick={() => void onRemoveDocument(document)}
                          >
                            Remove
                          </button>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          ) : null}
        </aside>
        {drawerOpen ? <div className="chat-scrim" aria-hidden="true" onClick={() => setDrawerOpen(false)} /> : null}

        <main className="chat-main">
          {loadError ? <p className="chat-error chat-banner" role="alert">{loadError}</p> : null}
          {!active ? (
            collectionsLoaded ? (
              <div className="chat-empty">
                <h2>Create your first knowledge base</h2>
                <p>A knowledge base is a set of PDFs, such as your HR policies. Create one, add PDFs, then ask questions.</p>
              </div>
            ) : null
          ) : (
            <>
              <section className="chat-thread" aria-label="Conversation">
                {turns.length === 0 ? (
                  <div className="chat-empty">
                    <h2>Ask about {active.name}</h2>
                    <p>
                      {readyCount > 0
                        ? "Ask a question in your own words. Each answer links to the PDF page it came from."
                        : "Add a PDF in the Documents panel. You can ask questions once it shows Ready."}
                    </p>
                  </div>
                ) : (
                  turns.map((turn) => (
                    <TurnView key={turn.id} turn={turn} onRetry={() => void ask(turn.question, turn.id)} onOpenSource={openSource} />
                  ))
                )}
                <div ref={threadEndRef} />
              </section>
              <form className="chat-composer" onSubmit={onSend}>
                <div className="chat-row">
                  <label htmlFor="chat-question" className="visually-hidden">Your question</label>
                  <textarea
                    id="chat-question"
                    rows={2}
                    value={question}
                    disabled={readyCount === 0}
                    placeholder={
                      readyCount > 0
                        ? "Ask a question about your documents…"
                        : "Add a PDF and wait until it is Ready"
                    }
                    onChange={(event) => setQuestion(event.target.value)}
                    onKeyDown={onComposerKey}
                  />
                  <button type="submit" className="chat-primary" disabled={readyCount === 0 || !question.trim() || asking}>
                    {asking ? "Answering…" : "Send"}
                  </button>
                </div>
                <p className="chat-hint">
                  Answers come only from documents in this knowledge base. Each question is answered on its own;
                  earlier messages are not used.
                </p>
              </form>
            </>
          )}
        </main>

        {source ? (
          <aside className="chat-source" aria-label="Source viewer">
            <div className="chat-panel-head">
              <h2>Source [{source.index}]</h2>
              <button type="button" className="chat-link-button" aria-label="Close source" onClick={closeSource}>
                Close
              </button>
            </div>
            <p className="chat-source-doc">
              {source.citation.document_name} · {pageLabel(source.citation)}
            </p>
            {source.evidence.length > 0 ? (
              <section aria-label="Quoted passage">
                <h3>Quoted passage</h3>
                {source.evidence.map((item) => (
                  <blockquote key={item.id}>
                    {item.text}
                    {item.truncated ? " …" : ""}
                  </blockquote>
                ))}
              </section>
            ) : (
              <p className="chat-muted">No passage text was returned for this source.</p>
            )}
            {source.error ? (
              <p className="chat-error" role="alert">{source.error}</p>
            ) : source.url ? (
              <>
                <iframe
                  title={`${source.citation.document_name} ${pageLabel(source.citation)}`}
                  src={`${source.url}#page=${source.citation.page_start}`}
                />
                <a href={`${source.url}#page=${source.citation.page_start}`} target="_blank" rel="noopener noreferrer">
                  Open PDF in a new tab
                </a>
              </>
            ) : (
              <p className="chat-muted">Loading PDF…</p>
            )}
          </aside>
        ) : null}
      </div>
    </div>
  );
}

function TurnView({
  turn,
  onRetry,
  onOpenSource,
}: {
  turn: Turn;
  onRetry: () => void;
  onOpenSource: (citation: Citation, index: number, evidence: Evidence[]) => void;
}) {
  return (
    <article className="chat-turn">
      <p className="chat-q">
        <span className="visually-hidden">You asked: </span>
        {turn.question}
      </p>
      {turn.state === "pending" ? (
        <div className="chat-a chat-a-pending" role="status">Searching your documents…</div>
      ) : turn.state === "error" ? (
        <div className="chat-a chat-a-error" role="alert">
          <p><strong>{turn.message}</strong></p>
          {turn.code ? <p className="chat-code">Failure code: {turn.code}</p> : null}
          {turn.retryable ? (
            <button type="button" onClick={onRetry}>Try again</button>
          ) : null}
        </div>
      ) : turn.response.status === "ANSWERED" ? (
        <div className="chat-a">
          <p className="chat-answer-text">{turn.response.answer}</p>
          {turn.response.citations.length > 0 ? (
            <>
              <p className="chat-sources-label">Sources</p>
              <ol className="chat-citations">
                {turn.response.citations.map((citation, index) => (
                  <li key={`${citation.document_id}-${citation.document_version_id}-${citation.page_start}-${citation.page_end}`}>
                    <button
                      type="button"
                      className="chat-cite"
                      aria-label={`Source ${index + 1}: ${citation.document_name}, ${pageLabel(citation)}`}
                      onClick={() => onOpenSource(citation, index + 1, turn.response.trace?.evidence ?? [])}
                    >
                      [{index + 1}] {citation.document_name} · {pageLabel(citation)}
                    </button>
                  </li>
                ))}
              </ol>
            </>
          ) : null}
        </div>
      ) : (
        <div className="chat-a chat-a-none">
          <p>
            <strong>{(NO_ANSWER_TEXT[turn.response.reason ?? ""] ?? NO_ANSWER_TEXT.MODEL_ABSTENTION).headline}</strong>
          </p>
          <p>{(NO_ANSWER_TEXT[turn.response.reason ?? ""] ?? NO_ANSWER_TEXT.MODEL_ABSTENTION).detail}</p>
          <p className="chat-code">Reason code: {turn.response.reason ?? "UNKNOWN"}</p>
        </div>
      )}
    </article>
  );
}
