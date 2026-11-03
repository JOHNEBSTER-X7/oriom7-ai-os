"use client";

import { useCallback, useEffect, useState } from "react";

type Evidence = {
  document_id: string; excerpt: string; title: string; url: string; provider: string;
  language: string | null; published_at: string | null; retrieved_at: string;
  rights_basis: string; robots_status: string;
};
type PendingAssertion = {
  assertion_id: string;
  subject: { id: string; type: string; name: string };
  predicate: string;
  object: { id: string; type: string; name: string };
  evidence: Evidence;
  confidence: number;
  extraction_method: string;
  submitted_by: string;
  created_at: string;
  valid_from: string | null;
  valid_to: string | null;
  status: "unverified";
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, credentials: "same-origin", cache: "no-store",
    headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}), ...init?.headers } });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const data = payload as { detail?: { code?: string; message?: string }; error?: string };
    throw new Error(data.detail?.message || data.detail?.code || data.error || `Request failed (${response.status})`);
  }
  return payload as T;
}

export default function EvidenceReviewCentre() {
  const [items, setItems] = useState<PendingAssertion[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState<Record<string, boolean>>({});
  const [filter, setFilter] = useState("");
  const [message, setMessage] = useState("Loading pending evidence assertions…");
  const limit = 20;

  const load = useCallback(async (nextOffset = 0, predicate = filter) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: String(limit), offset: String(nextOffset) });
      if (predicate.trim()) params.set("predicate", predicate.trim());
      const result = await request<{items: PendingAssertion[]; total: number}>(`/api/research/review-queue?${params}`);
      setItems(result.items); setTotal(result.total); setOffset(nextOffset);
      setConfirmed({});
      setMessage(result.total === 0 ? "There are no eligible unverified assertions awaiting review." :
        `Showing ${result.items.length} of ${result.total} pending assertion(s).`);
    } catch (error) {
      setItems([]); setTotal(0);
      setMessage(error instanceof Error ? error.message : "The review queue could not be loaded.");
    } finally { setLoading(false); }
  }, [filter]);

  useEffect(() => { void load(0, ""); }, [load]);

  async function decide(item: PendingAssertion, decision: "accepted" | "rejected") {
    if (!confirmed[item.assertion_id]) return;
    const label = decision === "accepted" ? "ACCEPT" : "REJECT";
    if (!window.confirm(`${label} this assertion? This decision will change its graph status and be recorded against your authenticated account.`)) return;
    setBusyId(item.assertion_id);
    try {
      await request(`/api/research/assertions/${item.assertion_id}/review`, {
        method: "POST", body: JSON.stringify({ decision }),
      });
      setMessage(`Assertion ${decision}. The review decision has been recorded.`);
      await load(offset);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The review decision could not be saved.");
    } finally { setBusyId(null); }
  }

  return (
    <div className="verification-workspace">
      <section className="research-intro">
        <p className="eyebrow">ORIOM7 · TRUST AND EVIDENCE</p>
        <h1>Evidence verification centre.</h1>
        <p>Inspect the original source context before deciding whether an AI-extracted relationship belongs in ORIOM7's accepted knowledge graph.</p>
      </section>

      <section className="verification-guidance" aria-labelledby="review-rules">
        <h2 id="review-rules">Review principles</h2>
        <ul>
          <li>Read the source itself, not only the extracted excerpt.</li>
          <li>Check whether the source actually supports the subject, relationship and object.</li>
          <li>Consider date, scope, qualifications, uncertainty and whether the claim is still current.</li>
          <li>Model confidence is an extraction score, not proof that a claim is true.</li>
          <li>Accept only when the evidence supports the complete relationship; otherwise reject or leave pending.</li>
        </ul>
        <p>Only accepted assertions are eligible for graph exploration and graph-aware assistant context. Review decisions are consequential and should be made by an authorised reviewer.</p>
      </section>

      <section className="verification-queue" aria-labelledby="queue-title">
        <div className="workspace-section-heading">
          <div><p className="eyebrow">HUMAN REVIEW QUEUE</p><h2 id="queue-title">Unverified assertions</h2></div>
          <span className="count-pill">{total} pending</span>
        </div>
        <form className="verification-filter" onSubmit={event => { event.preventDefault(); void load(0, filter); }}>
          <label htmlFor="predicate-filter">Filter by relationship type</label>
          <input id="predicate-filter" value={filter} onChange={event => setFilter(event.target.value)} placeholder="e.g. manufactures, founded_by" />
          <button className="secondary-button" type="submit" disabled={loading}>Apply filter</button>
          <button className="secondary-button" type="button" onClick={() => { setFilter(""); void load(0, ""); }}>Clear</button>
        </form>
        <p className="status" role="status" aria-live="polite">{message}</p>

        {loading ? <p role="status">Loading review records…</p> :
          items.length === 0 ? <p className="muted">No records match this filter. New extracted candidates will appear here only while their evidence remains eligible.</p> :
          <div className="verification-list">{items.map(item => <article className="verification-card" key={item.assertion_id}>
            <div className="verification-card-top">
              <span className="pending-label">UNVERIFIED</span>
              <span className="muted">Submitted {new Date(item.created_at).toLocaleString()}</span>
            </div>
            <h3 className="assertion-statement">
              <span>{item.subject.name}</span><span className="assertion-predicate">{item.predicate.replaceAll("_", " ")}</span><span>{item.object.name}</span>
            </h3>
            <dl className="assertion-metadata">
              <div><dt>Entity types</dt><dd>{item.subject.type} → {item.object.type}</dd></div>
              <div><dt>Extraction method</dt><dd>{item.extraction_method}</dd></div>
              <div><dt>Model confidence</dt><dd>{Math.round(item.confidence * 100)}% (not truth probability)</dd></div>
              <div><dt>Submitted by</dt><dd>{item.submitted_by}</dd></div>
              <div><dt>Validity dates</dt><dd>{item.valid_from || "Unknown start"} — {item.valid_to || "Unknown end"}</dd></div>
            </dl>

            <section className="evidence-source" aria-label="Supporting source">
              <div className="workspace-section-heading">
                <div><p className="eyebrow">SUPPORTING EVIDENCE</p><h4>{item.evidence.title || "Untitled source"}</h4></div>
                <a className="secondary-button source-open-link" href={item.evidence.url} target="_blank" rel="noreferrer">Open original source</a>
              </div>
              <blockquote>{item.evidence.excerpt}</blockquote>
              <dl className="assertion-metadata source-metadata">
                <div><dt>Provider</dt><dd>{item.evidence.provider || "Unspecified"}</dd></div>
                <div><dt>Language</dt><dd>{item.evidence.language || "Unspecified"}</dd></div>
                <div><dt>Published</dt><dd>{item.evidence.published_at ? new Date(item.evidence.published_at).toLocaleDateString() : "Not supplied"}</dd></div>
                <div><dt>Retrieved</dt><dd>{new Date(item.evidence.retrieved_at).toLocaleString()}</dd></div>
                <div><dt>Rights basis</dt><dd>{item.evidence.rights_basis}</dd></div>
                <div><dt>Robots status</dt><dd>{item.evidence.robots_status}</dd></div>
              </dl>
            </section>

            <div className="review-confirmation">
              <label>
                <input type="checkbox" checked={!!confirmed[item.assertion_id]} onChange={event => setConfirmed(old => ({...old, [item.assertion_id]: event.target.checked}))} />
                I have opened or otherwise inspected the original source and assessed whether it supports this complete relationship.
              </label>
            </div>
            <div className="review-actions">
              <button type="button" className="primary-button" disabled={!confirmed[item.assertion_id] || busyId === item.assertion_id} onClick={() => void decide(item, "accepted")}>
                {busyId === item.assertion_id ? "Saving…" : "Accept assertion"}
              </button>
              <button type="button" className="danger-button" disabled={!confirmed[item.assertion_id] || busyId === item.assertion_id} onClick={() => void decide(item, "rejected")}>Reject assertion</button>
            </div>
          </article>)}</div>}

        {total > limit && <nav className="queue-pagination" aria-label="Review queue pages">
          <button className="secondary-button" type="button" disabled={offset === 0 || loading} onClick={() => void load(Math.max(0, offset-limit))}>Previous</button>
          <span>Page {Math.floor(offset/limit)+1} of {Math.ceil(total/limit)}</span>
          <button className="secondary-button" type="button" disabled={offset+limit >= total || loading} onClick={() => void load(offset+limit)}>Next</button>
        </nav>}
      </section>
      <p className="research-disclaimer">The review API requires an authenticated user and a server-held review token. The token is never sent to the browser. Decisions cannot be reversed through this interface; corrections require a separately governed workflow.</p>
    </div>
  );
}
