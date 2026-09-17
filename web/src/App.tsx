import { FormEvent, useEffect, useState } from "react";
import { apiFetch } from "./api";
import { getApiKey, setApiKey } from "./auth";

type Probe = "unknown" | "ok" | "failed";

export function App() {
  const [keyInput, setKeyInput] = useState("");
  const [connected, setConnected] = useState(() => Boolean(getApiKey()));
  const [gateError, setGateError] = useState<string | null>(null);
  const [health, setHealth] = useState<Probe>("unknown");
  const [ready, setReady] = useState<Probe>("unknown");

  useEffect(() => {
    if (!connected) {
      return;
    }
    let cancelled = false;
    async function probe() {
      const [healthRes, readyRes] = await Promise.all([
        apiFetch("/health"),
        apiFetch("/ready"),
      ]);
      if (cancelled) {
        return;
      }
      setHealth(healthRes.ok ? "ok" : "failed");
      setReady(readyRes.ok ? "ok" : "failed");
    }
    void probe().catch(() => {
      if (!cancelled) {
        setHealth("failed");
        setReady("failed");
      }
    });
    return () => {
      cancelled = true;
    };
  }, [connected]);

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
          <p className="empty">Create a collection in the next phase.</p>
        </section>
      )}
    </main>
  );
}
