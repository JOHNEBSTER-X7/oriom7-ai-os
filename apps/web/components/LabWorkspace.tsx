"use client";

import { useEffect, useState } from "react";

type Project = {
  project_id: string; title: string; description: string | null; discipline: string;
  objectives: string[]; status: string; created_at: string; updated_at: string;
};
type Experiment = {
  experiment_id: string; project_id: string; title: string; hypothesis: string | null;
  protocol: string | null; configuration: Record<string, unknown>; status: string;
  created_at: string; updated_at: string;
};
type Equipment = {
  equipment_id: string; name: string; category: string; manufacturer: string | null;
  model: string | null; asset_tag: string | null; location: string | null;
  status: string; metadata: Record<string, unknown>;
};
type ListResponse<T> = { items: T[]; total: number };
type ApiError = { detail?: { message?: string; code?: string }; error?: string };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init, credentials: "same-origin", cache: "no-store",
    headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}), ...init?.headers },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = payload as ApiError;
    throw new Error(error.detail?.message || error.detail?.code || error.error || `Request failed (${response.status})`);
  }
  return payload as T;
}

export default function LabWorkspace() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [equipment, setEquipment] = useState<Equipment[]>([]);
  const [projectTitle, setProjectTitle] = useState("");
  const [discipline, setDiscipline] = useState("ai");
  const [experimentTitle, setExperimentTitle] = useState("");
  const [hypothesis, setHypothesis] = useState("");
  const [equipmentName, setEquipmentName] = useState("");
  const [equipmentCategory, setEquipmentCategory] = useState("electronics");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Loading your research workspace…");
  const [error, setError] = useState(false);

  const selectedProject = projects.find(project => project.project_id === selectedProjectId) || null;

  async function loadProjects(preferredId?: string) {
    const result = await api<ListResponse<Project>>("/api/labs/projects?limit=100");
    setProjects(result.items || []);
    const nextId = preferredId || selectedProjectId || result.items?.[0]?.project_id || "";
    setSelectedProjectId(nextId);
    return nextId;
  }

  async function loadExperiments(projectId: string) {
    if (!projectId) { setExperiments([]); return; }
    const result = await api<ListResponse<Experiment>>(`/api/labs/projects/${projectId}/experiments?limit=100`);
    setExperiments(result.items || []);
  }

  async function loadEquipment() {
    const result = await api<ListResponse<Equipment>>("/api/labs/equipment?limit=100");
    setEquipment(result.items || []);
  }

  async function refresh(projectId?: string) {
    const id = await loadProjects(projectId);
    await Promise.all([loadExperiments(id), loadEquipment()]);
  }

  useEffect(() => {
    refresh().then(() => setMessage("Workspace ready. Create a research project or register laboratory equipment."))
      .catch(err => { setError(true); setMessage(err instanceof Error ? err.message : "Could not load the laboratory workspace."); });
    // Load once on mount; selection changes are handled by the selection effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedProjectId) { setExperiments([]); return; }
    loadExperiments(selectedProjectId).catch(err => {
      setError(true); setMessage(err instanceof Error ? err.message : "Could not load experiments.");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProjectId]);

  async function createProject(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!projectTitle.trim()) return;
    setBusy(true); setError(false); setMessage("Creating research project…");
    try {
      const project = await api<Project>("/api/labs/projects", {
        method: "POST", body: JSON.stringify({ title: projectTitle, discipline }),
      });
      setProjectTitle("");
      await refresh(project.project_id);
      setMessage(`Created project: ${project.title}`);
    } catch (err) {
      setError(true); setMessage(err instanceof Error ? err.message : "Project creation failed.");
    } finally { setBusy(false); }
  }

  async function createExperiment(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProjectId || !experimentTitle.trim()) return;
    setBusy(true); setError(false); setMessage("Registering experiment plan…");
    try {
      await api<Experiment>(`/api/labs/projects/${selectedProjectId}/experiments`, {
        method: "POST", body: JSON.stringify({
          title: experimentTitle, hypothesis: hypothesis || null, configuration: {},
        }),
      });
      setExperimentTitle(""); setHypothesis("");
      await loadExperiments(selectedProjectId);
      setMessage("Experiment plan registered.");
    } catch (err) {
      setError(true); setMessage(err instanceof Error ? err.message : "Experiment registration failed.");
    } finally { setBusy(false); }
  }

  async function appendStatus(experiment: Experiment, nextStatus: string) {
    setBusy(true); setError(false); setMessage(`Updating experiment to ${nextStatus}…`);
    try {
      await api(`/api/labs/experiments/${experiment.experiment_id}/events`, {
        method: "POST",
        body: JSON.stringify({
          event_type: "status_change",
          summary: `Experiment status changed to ${nextStatus}`,
          data: { status: nextStatus },
        }),
      });
      await loadExperiments(selectedProjectId);
      setMessage(`Experiment status updated to ${nextStatus}.`);
    } catch (err) {
      setError(true); setMessage(err instanceof Error ? err.message : "Status update failed.");
    } finally { setBusy(false); }
  }

  async function registerEquipment(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!equipmentName.trim()) return;
    setBusy(true); setError(false); setMessage("Registering equipment…");
    try {
      await api<Equipment>("/api/labs/equipment", {
        method: "POST",
        body: JSON.stringify({ name: equipmentName, category: equipmentCategory }),
      });
      setEquipmentName("");
      await loadEquipment();
      setMessage("Equipment registered.");
    } catch (err) {
      setError(true); setMessage(err instanceof Error ? err.message : "Equipment registration failed.");
    } finally { setBusy(false); }
  }

  return (
    <div className="lab-workspace">
      <section className="research-intro">
        <p className="eyebrow">ORIOM7 · RESEARCH OPERATIONS</p>
        <h1>Laboratory workspace.</h1>
        <p>Organise research projects, register experiment plans and maintain an equipment inventory. This workspace records research activity; it does not control laboratory equipment or certify experimental results.</p>
      </section>

      <p className="status" role="status" aria-live="polite" data-kind={error ? "error" : "success"}>{message}</p>

      <section className="lab-grid" aria-label="Research workspace overview">
        <article className="research-search-card">
          <p className="eyebrow">01 · PROJECT PORTFOLIO</p>
          <h2>Research projects</h2>
          <form className="research-form" onSubmit={createProject}>
            <label htmlFor="lab-project-title">Project title</label>
            <input id="lab-project-title" value={projectTitle} onChange={e => setProjectTitle(e.target.value)} maxLength={160} required />
            <label htmlFor="lab-project-discipline">Research discipline</label>
            <select id="lab-project-discipline" value={discipline} onChange={e => setDiscipline(e.target.value)}>
              {["ai","semiconductors","computing","robotics","automotive","networking","cybersecurity","materials","energy","aerospace","biotechnology","healthcare","manufacturing","agriculture","mining","fintech","commerce","other"].map(item =>
                <option key={item} value={item}>{item.replace(/_/g, " ")}</option>)}
            </select>
            <button className="primary-button" type="submit" disabled={busy || !projectTitle.trim()}>{busy ? "Saving…" : "Create project"}</button>
          </form>
          <div className="lab-list" aria-label="Your projects">
            {projects.length === 0 ? <p className="muted">No projects yet.</p> : projects.map(project =>
              <button key={project.project_id} type="button" className={project.project_id === selectedProjectId ? "lab-list-item selected" : "lab-list-item"} onClick={() => setSelectedProjectId(project.project_id)}>
                <strong>{project.title}</strong><span>{project.discipline} · {project.status}</span>
              </button>)}
          </div>
        </article>

        <article className="research-search-card">
          <p className="eyebrow">02 · EXPERIMENT REGISTER</p>
          <h2>{selectedProject ? selectedProject.title : "Select a project"}</h2>
          {selectedProject ? <>
            <form className="research-form" onSubmit={createExperiment}>
              <label htmlFor="lab-experiment-title">Experiment title</label>
              <input id="lab-experiment-title" value={experimentTitle} onChange={e => setExperimentTitle(e.target.value)} maxLength={160} required />
              <label htmlFor="lab-experiment-hypothesis">Hypothesis or research question</label>
              <textarea id="lab-experiment-hypothesis" value={hypothesis} onChange={e => setHypothesis(e.target.value)} rows={3} maxLength={4000} />
              <button className="primary-button" type="submit" disabled={busy || !experimentTitle.trim()}>Register experiment</button>
            </form>
            <div className="lab-list">
              {experiments.length === 0 ? <p className="muted">No experiments registered for this project.</p> : experiments.map(experiment =>
                <div className="lab-list-item" key={experiment.experiment_id}>
                  <strong>{experiment.title}</strong>
                  <span>{experiment.status}{experiment.hypothesis ? ` · ${experiment.hypothesis}` : ""}</span>
                  <div className="lab-actions">
                    {experiment.status === "planned" && <button className="secondary-button" disabled={busy} onClick={() => appendStatus(experiment, "queued")}>Queue</button>}
                    {experiment.status === "queued" && <button className="secondary-button" disabled={busy} onClick={() => appendStatus(experiment, "running")}>Start</button>}
                    {experiment.status === "running" && <>
                      <button className="secondary-button" disabled={busy} onClick={() => appendStatus(experiment, "completed")}>Complete</button>
                      <button className="secondary-button" disabled={busy} onClick={() => appendStatus(experiment, "failed")}>Mark failed</button>
                    </>}
                  </div>
                </div>)}
            </div>
          </> : <p className="muted">Create or select a project to register experiment plans.</p>}
        </article>

        <article className="research-search-card">
          <p className="eyebrow">03 · EQUIPMENT REGISTER</p>
          <h2>Laboratory equipment</h2>
          <form className="research-form" onSubmit={registerEquipment}>
            <label htmlFor="lab-equipment-name">Equipment name</label>
            <input id="lab-equipment-name" value={equipmentName} onChange={e => setEquipmentName(e.target.value)} maxLength={160} required />
            <label htmlFor="lab-equipment-category">Category</label>
            <select id="lab-equipment-category" value={equipmentCategory} onChange={e => setEquipmentCategory(e.target.value)}>
              {["electronics","compute","robotics","mechanical","optical","telecommunications","materials","energy","environmental","other"].map(item => <option key={item}>{item}</option>)}
            </select>
            <button className="primary-button" type="submit" disabled={busy || !equipmentName.trim()}>Register equipment</button>
          </form>
          <div className="lab-list">
            {equipment.length === 0 ? <p className="muted">No equipment registered.</p> : equipment.map(item =>
              <div className="lab-list-item" key={item.equipment_id}>
                <strong>{item.name}</strong><span>{item.category} · {item.status}</span>
              </div>)}
          </div>
        </article>
      </section>
    </div>
  );
}
