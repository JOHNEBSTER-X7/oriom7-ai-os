"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Product = { code: string; name: string; status: string; unit: string; description: string };
type ApiKey = { api_key_id: string; name: string; key_prefix: string; plan_code: string; created_at: string; last_used_at?: string | null; revoked_at?: string | null };
type Usage = { product_code: string; requests: number; units: number; first_request?: string | null; last_request?: string | null };

const statusLabel: Record<string, string> = {
  planned: "Coming soon", preview: "Preview", existing_core_preview: "Core preview",
};

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, headers: { "content-type": "application/json", ...(init?.headers || {}) }, cache: "no-store" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || payload.error || `Request failed (${response.status})`);
  return payload as T;
}

export default function DeveloperPortal() {
  const [products, setProducts] = useState<Product[]>([]);
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [usage, setUsage] = useState<Usage[]>([]);
  const [keyName, setKeyName] = useState("My first integration");
  const [newKey, setNewKey] = useState("");
  const [usageKey, setUsageKey] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [catalogue, keyData] = await Promise.all([
        requestJson<{ products: Product[] }>("/api/developer/products"),
        requestJson<{ keys: ApiKey[] }>("/api/developer/keys"),
      ]);
      setProducts(catalogue.products || []);
      setKeys(keyData.keys || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load developer portal.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const activeKeys = useMemo(() => keys.filter((key) => !key.revoked_at), [keys]);

  async function createKey(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setNotice(""); setNewKey("");
    try {
      const result = await requestJson<{ key: string }>("/api/developer/keys", {
        method: "POST", body: JSON.stringify({ name: keyName, plan_code: "starter" }),
      });
      setNewKey(result.key);
      setNotice("API key created. Copy it now; it will not be shown again.");
      await load();
    } catch (err) { setError(err instanceof Error ? err.message : "Could not create API key."); }
    finally { setBusy(false); }
  }

  async function revokeKey(id: string) {
    if (!window.confirm("Revoke this API key? Integrations using it will stop working.")) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await requestJson(`/api/developer/keys/${id}`, { method: "DELETE" });
      setNotice("API key revoked."); await load();
    } catch (err) { setError(err instanceof Error ? err.message : "Could not revoke API key."); }
    finally { setBusy(false); }
  }

  async function loadUsage(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setUsage([]);
    try {
      const result = await requestJson<{ usage: Usage[] }>("/api/developer/usage", {
        headers: { authorization: `Bearer ${usageKey.trim()}` },
      });
      setUsage(result.usage || []);
    } catch (err) { setError(err instanceof Error ? err.message : "Could not load usage."); }
    finally { setBusy(false); }
  }

  return (
    <main className="developer-shell">
      <header className="site-header developer-header">
        <a className="brand" href="/" aria-label="ORIOM7 home">ORIOM7</a>
        <span className="header-caption">Developer platform</span>
        <a className="workspace-link" href="/research">Research workspace</a>
      </header>

      <section className="developer-hero">
        <p className="eyebrow">ORIOM7 · DEVELOPER CONSOLE</p>
        <h1>Build with intelligence.</h1>
        <p>Explore ORIOM7 APIs, manage developer credentials and monitor usage from one workspace.</p>
        <div className="developer-hero-actions">
          <a className="primary-button" href="#api-keys">Create an API key</a>
          <a className="secondary-button" href="/api-docs">API documentation</a>
        </div>
      </section>

      {error && <div className="developer-alert error" role="alert">{error}</div>}
      {notice && <div className="developer-alert success" role="status">{notice}</div>}
      {loading && <p role="status">Loading developer workspace…</p>}

      <section className="developer-stats" aria-label="Developer account summary">
        <article><span>Available products</span><strong>{products.length}</strong></article>
        <article><span>Active API keys</span><strong>{activeKeys.length}</strong></article>
        <article><span>Billing</span><strong>Not configured</strong></article>
      </section>

      <section className="developer-section" aria-labelledby="products-heading">
        <div className="developer-section-heading"><div><p className="eyebrow">API CATALOGUE</p><h2 id="products-heading">Products and services</h2></div><span className="muted">Availability is shown honestly</span></div>
        <div className="developer-product-grid">
          {products.map((product) => <article className="developer-product-card" key={product.code}>
            <div className="developer-product-top"><span className="developer-product-code">{product.code}</span><span className={`developer-badge ${product.status}`}>{statusLabel[product.status] || product.status}</span></div>
            <h3>{product.name}</h3><p>{product.description}</p>
            <div className="developer-product-footer"><span>Metered by {product.unit.replaceAll("_", " ")}</span><span>API</span></div>
          </article>)}
        </div>
      </section>

      <section className="developer-section developer-two-column" id="api-keys">
        <article className="developer-panel">
          <p className="eyebrow">CREDENTIALS</p><h2>Create an API key</h2>
          <p className="muted">Keys are shown once. Store them securely and never commit them to source control.</p>
          <form className="developer-form" onSubmit={createKey}>
            <label htmlFor="key-name">Key name</label>
            <input id="key-name" value={keyName} onChange={(event) => setKeyName(event.target.value)} maxLength={80} minLength={1} required />
            <button className="primary-button" disabled={busy}>{busy ? "Please wait…" : "Generate API key"}</button>
          </form>
          {newKey && <div className="new-key-box"><strong>Copy your new key now</strong><code>{newKey}</code><button className="secondary-button" onClick={() => void navigator.clipboard.writeText(newKey)}>Copy key</button></div>}
        </article>

        <article className="developer-panel">
          <p className="eyebrow">ACCOUNT SECURITY</p><h2>Your API keys</h2>
          {keys.length === 0 ? <p className="muted">No keys have been created yet.</p> : <ul className="developer-key-list">
            {keys.map((key) => <li key={key.api_key_id}>
              <div><strong>{key.name}</strong><code>{key.key_prefix}••••••••</code><small>{key.plan_code} · Created {new Date(key.created_at).toLocaleDateString()}</small></div>
              {key.revoked_at ? <span className="developer-badge planned">Revoked</span> : <button className="danger-button" disabled={busy} onClick={() => void revokeKey(key.api_key_id)}>Revoke</button>}
            </li>)}
          </ul>}
        </article>
      </section>

      <section className="developer-section developer-panel">
        <p className="eyebrow">OBSERVABILITY</p><h2>Usage overview</h2>
        <p className="muted">Enter an active API key to retrieve its current calendar-month usage. The key is used for this request only and is not saved by this page.</p>
        <form className="developer-usage-form" onSubmit={loadUsage}>
          <label className="sr-only" htmlFor="usage-key">API key for usage lookup</label>
          <input id="usage-key" type="password" autoComplete="off" placeholder="oriom_live_…" value={usageKey} onChange={(event) => setUsageKey(event.target.value)} required />
          <button className="primary-button" disabled={busy || !usageKey.trim()}>Load usage</button>
        </form>
        {usage.length > 0 && <div className="developer-table-wrap"><table className="developer-table"><thead><tr><th>Product</th><th>Requests</th><th>Units</th></tr></thead><tbody>{usage.map((row) => <tr key={row.product_code}><td>{row.product_code}</td><td>{row.requests}</td><td>{row.units}</td></tr>)}</tbody></table></div>}
        {usage.length === 0 && <p className="note">No usage rows loaded. Billing and invoice totals are not available yet.</p>}
      </section>

      <section className="developer-launch-note"><strong>Launch readiness:</strong> Product providers, trusted sign-in, plan enforcement and payment processing must be configured before commercial availability. Current product status labels are not purchase or service guarantees.</section>
    </main>
  );
}
