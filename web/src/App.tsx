import { FormEvent, useEffect, useState } from "react";
import { apiFetch } from "./api";
import { clearApiKey, getApiKey, setApiKey } from "./auth";

type Probe = "unknown" | "ok" | "failed";
type Collection = { collection_id: string; name: string; status: string };
type Document = { document_id: string; logical_name: string; status: string | null; failure_code?: string | null };
const POLL_LIMIT = 60;

function collectionIdFromPath(): string | null {
  return window.location.pathname.match(/^\/collections\/([^/]+)$/)?.[1] ?? null;
}

export function App() {
  const [keyInput, setKeyInput] = useState("");
  const [connected, setConnected] = useState(() => Boolean(getApiKey()));
  const [gateError, setGateError] = useState<string | null>(null);
  const [health, setHealth] = useState<Probe>("unknown");
  const [ready, setReady] = useState<Probe>("unknown");
  const [collections, setCollections] = useState<Collection[]>([]);
  const [collectionsError, setCollectionsError] = useState<string | null>(null);
  const [collectionName, setCollectionName] = useState("");
  const [collectionError, setCollectionError] = useState<string | null>(null);
  const [selectedCollectionId, setSelectedCollectionId] = useState(collectionIdFromPath);
  const [refresh, setRefresh] = useState(0);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    if (!connected) {
      return;
    }
    let cancelled = false;
    async function loadWorkspace() {
      const [healthRes, readyRes, collectionsRes] = await Promise.all([
        apiFetch("/health"),
        apiFetch("/ready"),
        apiFetch("/v1/collections"),
      ]);
      if (cancelled) {
        return;
      }
      setHealth(healthRes.ok ? "ok" : "failed");
      setReady(readyRes.ok ? "ok" : "failed");
      if (collectionsRes.status === 401) {
        clearApiKey();
        setConnected(false);
        return;
      }
      if (!collectionsRes.ok) {
        setCollectionsError("Collections are unavailable.");
        return;
      }
      setCollections(await collectionsRes.json());
      setCollectionsError(null);
    }
    void loadWorkspace().catch(() => {
      if (!cancelled) {
        setHealth("failed");
        setReady("failed");
        setCollectionsError("Collections are unavailable.");
      }
    });
    return () => {
      cancelled = true;
    };
  }, [connected, refresh]);

  useEffect(() => {
    function onPopState() {
      setSelectedCollectionId(collectionIdFromPath());
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (!selectedCollectionId || !connected) return;
    void apiFetch(`/v1/collections/${selectedCollectionId}/documents`)
      .then(async (response) => response.ok && setDocuments(await response.json()))
      .catch(() => setUploadError("Documents are unavailable."));
  }, [connected, selectedCollectionId]);

  function onConnect(event: FormEvent) {
    event.preventDefault();
    const trimmed = keyInput.trim();
    if (!trimmed) {
      setGateError("API key is required");
      return;
    }
    setApiKey(trimmed);
    setGateError(null);
    setConnected(true);
  }

  async function onCreateCollection(event: FormEvent) {
    event.preventDefault();
    const name = collectionName.trim();
    if (!name) {
      setCollectionError("Collection name is required");
      return;
    }
    const response = await apiFetch("/v1/collections", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (response.status === 401) {
      clearApiKey();
      setConnected(false);
      return;
    }
    if (!response.ok) {
      setCollectionError("Collection could not be created.");
      return;
    }
    const collection = (await response.json()) as Collection;
    setCollections((current) => [...current, collection]);
    setCollectionName("");
    setCollectionError(null);
  }

  function openCollection(collectionId: string) {
    window.history.pushState({}, "", collectionId ? `/collections/${collectionId}` : "/");
    setSelectedCollectionId(collectionId);
  }

  async function pollDocument(documentId: string, attempt = 0) {
    const response = await apiFetch(`/v1/documents/${documentId}`);
    if (!response.ok) return;
    const document = (await response.json()) as Document;
    setDocuments((current) => [...current.filter((item) => item.document_id !== documentId), document]);
    if (document.status !== "READY" && document.status !== "FAILED") {
      if (attempt === POLL_LIMIT) {
        setUploadError("Ingestion is still waiting. Try again shortly.");
        return;
      }
      window.setTimeout(() => void pollDocument(documentId, attempt + 1), 1000);
    }
  }

  async function onUpload(event: FormEvent) {
    event.preventDefault();
    if (!file || !selectedCollectionId) {
      setUploadError("Choose a PDF first.");
      return;
    }
    const body = new FormData();
    body.append("file", file);
    const response = await apiFetch(`/v1/collections/${selectedCollectionId}/documents`, {
      method: "POST",
      body,
    });
    if (!response.ok) {
      const error = (await response.json()) as { detail?: string };
      setUploadError(error.detail ? `Upload failed: ${error.detail}.` : "Upload failed.");
      return;
    }
    const uploaded = (await response.json()) as { document_id: string };
    setDocuments((current) => [
      ...current.filter((document) => document.document_id !== uploaded.document_id),
      { document_id: uploaded.document_id, logical_name: file.name, status: "QUEUED" },
    ]);
    setFile(null);
    setUploadError(null);
    await pollDocument(uploaded.document_id);
  }

  const selectedCollection = collections.find(
    (collection) => collection.collection_id === selectedCollectionId,
  );

  return (
    <main className="shell">
      <header className="mast">
        <p className="kicker">Cited RAG Bot</p>
        <h1>Glass-box console</h1>
        <p className="lede">
          Answers only from collection PDFs. Citations are application-owned.
        </p>
      </header>

      {!connected ? (
        <form className="gate" onSubmit={onConnect}>
          <label htmlFor="api-key">API key</label>
          <input
            id="api-key"
            name="api-key"
            type="password"
            autoComplete="off"
            value={keyInput}
            onChange={(event) => setKeyInput(event.target.value)}
          />
          {gateError ? <p className="error">{gateError}</p> : null}
          <button type="submit">Connect</button>
        </form>
      ) : (
        <section className="workspace">
          <ul className="badges" aria-label="API status">
            <li data-status={health}>
              health <strong>{health}</strong>
            </li>
            <li data-status={ready}>
              ready <strong>{ready}</strong>
            </li>
          </ul>
          {selectedCollection ? (
            <section className="collection-shell">
              <a
                href="/"
                onClick={(event) => {
                  event.preventDefault();
                  openCollection("");
                }}
              >
                Back to collections
              </a>
              <h2>{selectedCollection.name}</h2>
              <form onSubmit={onUpload}>
                <label htmlFor="upload-pdf">Upload PDF</label>
                <input
                  id="upload-pdf"
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
                <button type="submit">Upload</button>
              </form>
              {uploadError ? <p className="error">{uploadError}</p> : null}
              {documents.length === 0 ? <p className="empty">No documents yet.</p> : (
                <ul className="collections">
                  {documents.map((document) => <li key={document.document_id}>
                    {document.logical_name} — <strong>{document.status}</strong>
                    {document.failure_code ? <span> ({document.failure_code})</span> : null}
                  </li>)}
                </ul>
              )}
              <p className="empty">Questions arrive in UI-03.</p>
            </section>
          ) : (
            <>
              <form className="collection-form" onSubmit={onCreateCollection}>
                <label htmlFor="collection-name">Collection name</label>
                <input
                  id="collection-name"
                  value={collectionName}
                  onChange={(event) => setCollectionName(event.target.value)}
                />
                {collectionError ? <p className="error">{collectionError}</p> : null}
                <button type="submit">Create collection</button>
              </form>
              {collectionsError ? (
                <p className="error">
                  {collectionsError} <button onClick={() => setRefresh((value) => value + 1)}>Retry</button>
                </p>
              ) : collections.length === 0 ? (
                <p className="empty">No collections yet.</p>
              ) : (
                <ul className="collections">
                  {collections.map((collection) => (
                    <li key={collection.collection_id}>
                      <a
                        href={`/collections/${collection.collection_id}`}
                        onClick={(event) => {
                          event.preventDefault();
                          openCollection(collection.collection_id);
                        }}
                      >
                        {collection.name}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </section>
      )}
    </main>
  );
}
