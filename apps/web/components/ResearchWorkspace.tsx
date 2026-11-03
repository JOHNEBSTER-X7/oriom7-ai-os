"use client";

import { useMemo, useState } from "react";

type SearchResult = {
  id: string; title: string; url: string; snippet: string; source_type: string;
  provider: string; retrieved_at: string; published_at: string | null; language: string | null;
};
type Entity = { id: string; type: string; name: string };
type Relation = {
  id: string; subject: Entity; predicate: string; object: Entity;
  evidence: { document_id: string; excerpt: string; title?: string; url?: string; published_at?: string | null; retrieved_at?: string };
  confidence: number; created_at: string; valid_from?: string | null; valid_to?: string | null;
};
type PathRecord = { depth: number; entity_ids: string[]; edges: Array<Record<string, unknown>> };
type ApiError = { detail?: { message?: string; code?: string }; error?: string };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, credentials: "same-origin", cache: "no-store",
    headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}), ...init?.headers } });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = payload as ApiError;
    throw new Error(error.detail?.message || error.detail?.code || error.error || `Request failed (${response.status})`);
  }
  return payload as T;
}

export default function ResearchWorkspace() {
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [relations, setRelations] = useState<Relation[]>([]);
  const [paths, setPaths] = useState<PathRecord[]>([]);
  const [answer, setAnswer] = useState("");
  const [answerSources, setAnswerSources] = useState<Array<{id:string;title:string;url:string}>>([]);
  const [graphCitations, setGraphCitations] = useState<Array<{id:string;title:string;url:string}>>([]);
  const [inconsistencies, setInconsistencies] = useState<Array<Record<string, unknown>>>([]);
  const [busy, setBusy] = useState(false);
  const [entityBusy, setEntityBusy] = useState(false);
  const [message, setMessage] = useState("Search the web index and explore accepted knowledge-graph relationships.");
  const [tab, setTab] = useState<"sources" | "graph" | "timeline">("sources");

  async function runResearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const clean = query.trim();
    if (!clean) return;
    setBusy(true); setMessage("Searching available ORIOM7 sources…");
    setAnswer(""); setAnswerSources([]); setGraphCitations([]); setInconsistencies([]);
    try {
      const [search, entitySearch] = await Promise.all([
        api<{results: SearchResult[]; status: string; unavailable_sources: string[]}>("/api/research/search", {
          method: "POST", body: JSON.stringify({ query: clean, limit: 12, sources: ["oriom7_index", "external"] }),
        }),
        api<{entities: Entity[]}>("/api/research/entities?q=" + encodeURIComponent(clean.slice(0, 190)) + "&limit=12"),
      ]);
      setSearchResults(search.results || []);
      setEntities(entitySearch.entities || []);
      if (search.unavailable_sources?.length) {
        setMessage(`Partial search: unavailable sources — ${search.unavailable_sources.join(", ")}. Results shown are from configured sources only.`);
      } else {
        setMessage(`Found ${search.results?.length || 0} source results and ${entitySearch.entities?.length || 0} matching graph entities.`);
      }
      const response = await api<{
        output_text: string;
        grounding?: { citations?: Array<{id:string;title:string;url:string}>; knowledge_graph?: {
          citations?: Array<{id:string;title:string;url:string}>;
          potential_inconsistencies?: Array<Record<string, unknown>>;
        } };
      }>("/api/research/assistant", { method: "POST", body: JSON.stringify({
        input: clean, mode: "research", max_output_tokens: 1800,
        grounding: { search: true, minimum_sources: 1 },
      }) });
      setAnswer(response.output_text || "");
      setAnswerSources(response.grounding?.citations || []);
      setGraphCitations(response.grounding?.knowledge_graph?.citations || []);
      setInconsistencies(response.grounding?.knowledge_graph?.potential_inconsistencies || []);
      if (!search.results?.length && !entitySearch.entities?.length) {
        setMessage("The request completed, but no matching search results or graph entities were found. Check that providers and the database are configured.");
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "ORIOM7 could not complete this research request.");
    } finally { setBusy(false); }
  }

  async function openEntity(entity: Entity) {
    setSelectedEntity(entity); setEntityBusy(true); setTab("graph");
    try {
      const [detail, pathData] = await Promise.all([
        api<{relations: Relation[]}>(`/api/research/entities/${entity.id}?limit=60`),
        api<{paths: PathRecord[]}>(`/api/research/entities/${entity.id}/paths?max_depth=3&limit=60`),
      ]);
      setRelations(detail.relations || []);
      setPaths(pathData.paths || []);
    } catch (error) {
      setRelations([]); setPaths([]);
      setMessage(error instanceof Error ? error.message : "The graph could not be loaded.");
    } finally { setEntityBusy(false); }
  }

  const graphNodes = useMemo(() => {
    if (!selectedEntity) return [];
    const map = new Map<string, Entity>();
    for (const relation of relations) {
      map.set(relation.subject.id, relation.subject);
      map.set(relation.object.id, relation.object);
    }
    map.delete(selectedEntity.id);
    return [...map.values()].slice(0, 10);
  }, [relations, selectedEntity]);

  const timeline = useMemo(() => [...relations].sort((a,b) =>
    (a.valid_from || a.created_at).localeCompare(b.valid_from || b.created_at)), [relations]);

  function downloadReport() {
    const lines = [
      "# ORIOM7 Research Report", "", `**Research question:** ${query}`,
      `**Generated:** ${new Date().toISOString()}`, "",
      "## Research synthesis", answer || "No assistant synthesis is available.",
      "", "## Search sources",
      ...searchResults.map((item, i) => `${i+1}. [${item.title}](${item.url}) — ${item.snippet}`),
      "", "## Knowledge graph",
      selectedEntity ? `Selected entity: ${selectedEntity.name}` : "No entity selected.",
      ...relations.map(item => `- ${item.subject.name} — ${item.predicate} → ${item.object.name}. Evidence: ${item.evidence.excerpt}`),
      "", "## Potential inconsistencies",
      ...inconsistencies.map(item => `- ${JSON.stringify(item)}`),
      "", "## Citation references",
      ...answerSources.map(item => `- [${item.id}] [${item.title}](${item.url})`),
      ...graphCitations.map(item => `- [${item.id}] [${item.title}](${item.url})`),
      "", "> Research output is evidence-assisted, not a guarantee of factual correctness. Graph relationships do not establish causation or transitive truth.",
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = "oriom7-research-report.md"; anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="research-workspace">
      <section className="research-intro">
        <p className="eyebrow">ORIOM7 · INTELLIGENCE WORKSPACE</p>
        <h1>Research beyond the search result.</h1>
        <p>Investigate topics, compare source material, explore relationships and assemble traceable research reports.</p>
      </section>

      <section className="research-search-card" aria-labelledby="research-search-title">
        <h2 id="research-search-title">Start an investigation</h2>
        <form className="research-form" onSubmit={runResearch}>
          <label htmlFor="research-query">Research question or subject</label>
          <textarea id="research-query" value={query} onChange={event => setQuery(event.target.value)}
            placeholder="Example: Which organisations are developing grid-scale battery storage, and how are they connected?"
            rows={3} maxLength={2000} />
          <div className="research-form-footer">
            <span className="muted">{query.length}/2000 characters</span>
            <button className="primary-button" type="submit" disabled={busy || !query.trim()}>
              {busy ? "Researching…" : "Research with ORIOM7"}
            </button>
          </div>
        </form>
        <p className="status" role="status" aria-live="polite">{message}</p>
      </section>

      {answer && <section className="research-answer-card" aria-labelledby="synthesis-title">
        <div className="workspace-section-heading">
          <div><p className="eyebrow">AI RESEARCH SYNTHESIS</p><h2 id="synthesis-title">Research brief</h2></div>
          <button className="secondary-button" type="button" onClick={downloadReport}>Export report</button>
        </div>
        <div className="research-answer">{answer}</div>
        {(answerSources.length > 0 || graphCitations.length > 0) && <div className="citation-list">
          <h3>Sources cited by the assistant</h3>
          {[...answerSources, ...graphCitations].map(source => <a key={source.id} href={source.url} target="_blank" rel="noreferrer">
            <strong>[{source.id}]</strong> {source.title}
          </a>)}
        </div>}
      </section>}

      {inconsistencies.length > 0 && <section className="inconsistency-panel" aria-labelledby="inconsistency-title">
        <h2 id="inconsistency-title">Potential evidence inconsistencies</h2>
        <p>These are review signals, not verified contradictions. Check dates, context and source scope before drawing conclusions.</p>
        <ul>{inconsistencies.map((item, index) => <li key={index}>{String(item.subject || "Entity")} — {String(item.predicate || "relationship")}: {String(item.claim_a_object || "claim A")} versus {String(item.claim_b_object || "claim B")}</li>)}</ul>
      </section>}

      {(searchResults.length > 0 || entities.length > 0) && <section className="research-results-grid">
        <aside className="research-entity-panel" aria-labelledby="entity-title">
          <div className="workspace-section-heading"><div><p className="eyebrow">ENTITY DISCOVERY</p><h2 id="entity-title">Knowledge entities</h2></div><span className="count-pill">{entities.length}</span></div>
          {entities.length === 0 ? <p className="muted">No matching entities were found in the accepted graph.</p> :
            <ul className="entity-list">{entities.map(entity => <li key={entity.id}>
              <button type="button" className={selectedEntity?.id === entity.id ? "entity-button selected" : "entity-button"} onClick={() => openEntity(entity)}>
                <span>{entity.name}</span><small>{entity.type.replaceAll("_", " ")}</small>
              </button>
            </li>)}</ul>}
        </aside>

        <section className="research-detail-panel" aria-label="Research evidence and graph explorer">
          <div className="research-tabs" role="tablist" aria-label="Research views">
            <button type="button" role="tab" aria-selected={tab === "sources"} className={tab === "sources" ? "active" : ""} onClick={() => setTab("sources")}>Source comparison</button>
            <button type="button" role="tab" aria-selected={tab === "graph"} className={tab === "graph" ? "active" : ""} onClick={() => setTab("graph")}>Relationship graph</button>
            <button type="button" role="tab" aria-selected={tab === "timeline"} className={tab === "timeline" ? "active" : ""} onClick={() => setTab("timeline")}>Timeline</button>
          </div>

          {tab === "sources" && <div className="source-comparison" role="tabpanel">
            <h2>Compare retrieved sources</h2>
            {searchResults.length === 0 ? <p className="muted">No search results are available for comparison.</p> :
              <div className="source-cards">{searchResults.map((source, index) => <article className="source-card" key={source.id}>
                <div className="source-card-meta"><span>Source {index + 1}</span><span>{source.provider}</span></div>
                <h3><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a></h3>
                <p>{source.snippet || "No extract available."}</p>
                <dl><div><dt>Published</dt><dd>{source.published_at ? new Date(source.published_at).toLocaleDateString() : "Not supplied"}</dd></div>
                  <div><dt>Retrieved</dt><dd>{new Date(source.retrieved_at).toLocaleDateString()}</dd></div>
                  <div><dt>Language</dt><dd>{source.language || "Unspecified"}</dd></div></dl>
              </article>)}</div>}
          </div>}

          {tab === "graph" && <div role="tabpanel" className="graph-panel">
            <div className="workspace-section-heading"><div><h2>Relationship explorer</h2><p className="muted">{selectedEntity ? `Connections around ${selectedEntity.name}` : "Choose an entity to explore its accepted relationships."}</p></div></div>
            {entityBusy ? <p role="status">Loading graph evidence…</p> : !selectedEntity ? <p className="muted">Select an entity from the list to explore its relationships.</p> :
              relations.length === 0 ? <p className="muted">No accepted relationships are currently available for this entity.</p> :
              <>
                <div className="graph-canvas">
                  <svg viewBox="0 0 640 390" role="img" aria-labelledby="graph-title graph-desc">
                    <title id="graph-title">Relationships connected to {selectedEntity.name}</title>
                    <desc id="graph-desc">A hub and spoke diagram. The central entity is connected to {graphNodes.length} entities through accepted source-backed relationships. The list below provides the same information in text.</desc>
                    {graphNodes.map((node, index) => {
                      const angle = (2 * Math.PI * index / Math.max(graphNodes.length, 1)) - Math.PI / 2;
                      const x = 320 + 220 * Math.cos(angle); const y = 190 + 135 * Math.sin(angle);
                      return <g key={node.id}>
                        <line x1="320" y1="190" x2={x} y2={y} stroke="currentColor" strokeWidth="1.5" opacity=".55" />
                        <circle cx={x} cy={y} r="34" fill="#f4e8e8" stroke="#7b1e24" strokeWidth="2" />
                        <text x={x} y={y+4} textAnchor="middle" fill="#191919" fontSize="10">{node.name.slice(0, 18)}</text>
                      </g>;
                    })}
                    <circle cx="320" cy="190" r="52" fill="#7b1e24" />
                    <text x="320" y="186" textAnchor="middle" fill="#ffffff" fontSize="12" fontWeight="700">{selectedEntity.name.slice(0, 18)}</text>
                    <text x="320" y="203" textAnchor="middle" fill="#ffffff" fontSize="9">selected entity</text>
                  </svg>
                </div>
                <ul className="relation-list">{relations.map(relation => <li key={relation.id}>
                  <strong>{relation.subject.name}</strong> <span className="relation-predicate">{relation.predicate.replaceAll("_", " ")}</span> <strong>{relation.object.name}</strong>
                  <p>{relation.evidence.excerpt}</p>
                  {relation.evidence.url && <a href={relation.evidence.url} target="_blank" rel="noreferrer">Open supporting source</a>}
                  <small>Confidence score: {Math.round(relation.confidence * 100)}% · Accepted assertion</small>
                </li>)}</ul>
                {paths.length > 0 && <details className="path-details"><summary>Bounded multi-hop paths ({paths.length})</summary>
                  <p className="muted">Paths contain accepted edges. A connection does not prove causation or transitive truth.</p>
                  {paths.map((path, index) => <p key={index}>Path {index+1}: {path.depth} relationship step(s), {path.edges.length} evidence-linked edge(s).</p>)}
                </details>}
              </>}
          </div>}

          {tab === "timeline" && <div role="tabpanel" className="timeline-panel">
            <h2>Historical relationship timeline</h2>
            {!selectedEntity ? <p className="muted">Select an entity to view its dated relationships.</p> :
              timeline.length === 0 ? <p className="muted">No accepted relationships are available for the timeline.</p> :
              <ol className="timeline-list">{timeline.map(relation => <li key={relation.id}>
                <time>{relation.valid_from || new Date(relation.created_at).toLocaleDateString()} {relation.valid_to ? `— ${relation.valid_to}` : ""}</time>
                <strong>{relation.subject.name} {relation.predicate.replaceAll("_", " ")} {relation.object.name}</strong>
                <p>{relation.evidence.excerpt}</p>
              </li>)}</ol>}
          </div>}
        </section>
      </section>}

      <p className="research-disclaimer">ORIOM7 displays evidence-backed research, not guaranteed truth. Availability depends on configured search providers, database migrations, accepted graph assertions and model-provider access. Graph relationships are not proof of causation.</p>
    </div>
  );
}
