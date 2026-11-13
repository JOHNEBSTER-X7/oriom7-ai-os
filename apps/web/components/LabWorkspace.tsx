"use client";

import { useEffect, useState } from "react";
import LabInventoryPanel from "./LabInventoryPanel";

type Project = {
  project_id: string; title: string; description: string | null; discipline: string;
  objectives: string[]; status: string; created_at: string; updated_at: string;
};
type Experiment = {
  experiment_id: string; project_id: string; title: string; hypothesis: string | null;
  protocol: string | null; configuration: Record<string, unknown>; status: string;
  created_at: string; updated_at: string;
};
type NotebookEntry = { entry_id: string; entry_type: string; title: string; content: string; experiment_id: string | null; created_at: string };
type EquipmentSummary = { total_assets: number; available_assets: number; in_use_assets: number; maintenance_assets: number; retired_assets: number; calibration_attention_assets: number; active_bookings: number; maintenance_due_30_days: number; overdue_maintenance_assets: number };
type Equipment = {
  equipment_id: string; name: string; category: string; manufacturer: string | null;
  model: string | null; asset_tag: string | null; location: string | null;
  status: string; metadata: Record<string, unknown>;
};
type Calibration = { calibration_id: string; calibrated_on: string; due_on: string | null; outcome: string; performed_by: string; certificate_reference: string | null; notes: string | null; created_at: string };
type MaintenanceRecord = { maintenance_id: string; maintenance_type: string; description: string; performed_by: string; performed_at: string; next_due_at: string | null };
type EquipmentBooking = { booking_id: string; purpose: string; booked_by: string; starts_at: string; ends_at: string; status: string };
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
  const [equipmentSummary, setEquipmentSummary] = useState<EquipmentSummary | null>(null);
  const [selectedEquipmentId, setSelectedEquipmentId] = useState("");
  const [calibrations, setCalibrations] = useState<Calibration[]>([]);
  const [maintenanceRecords, setMaintenanceRecords] = useState<MaintenanceRecord[]>([]);
  const [bookings, setBookings] = useState<EquipmentBooking[]>([]);
  const [notebookEntries, setNotebookEntries] = useState<NotebookEntry[]>([]);
  const [projectTitle, setProjectTitle] = useState("");
  const [discipline, setDiscipline] = useState("ai");
  const [experimentTitle, setExperimentTitle] = useState("");
  const [hypothesis, setHypothesis] = useState("");
  const [equipmentName, setEquipmentName] = useState("");
  const [equipmentCategory, setEquipmentCategory] = useState("electronics");
  const [equipmentAssetTag, setEquipmentAssetTag] = useState("");
  const [equipmentLocation, setEquipmentLocation] = useState("");
  const [calibrationDate, setCalibrationDate] = useState("");
  const [calibrationDueDate, setCalibrationDueDate] = useState("");
  const [calibrationOutcome, setCalibrationOutcome] = useState("pass");
  const [calibrationPerformer, setCalibrationPerformer] = useState("");
  const [calibrationCertificate, setCalibrationCertificate] = useState("");
  const [maintenanceType, setMaintenanceType] = useState("preventive");
  const [maintenanceDescription, setMaintenanceDescription] = useState("");
  const [maintenancePerformer, setMaintenancePerformer] = useState("");
  const [maintenancePerformedAt, setMaintenancePerformedAt] = useState("");
  const [maintenanceNextDue, setMaintenanceNextDue] = useState("");
  const [bookingPurpose, setBookingPurpose] = useState("");
  const [bookingBy, setBookingBy] = useState("");
  const [bookingStart, setBookingStart] = useState("");
  const [bookingEnd, setBookingEnd] = useState("");
  const [notebookType, setNotebookType] = useState("observation");
  const [notebookTitle, setNotebookTitle] = useState("");
  const [notebookContent, setNotebookContent] = useState("");
  const [notebookExperimentId, setNotebookExperimentId] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Loading your research workspace…");
  const [error, setError] = useState(false);

  const selectedProject = projects.find(project => project.project_id === selectedProjectId) || null;
  const selectedEquipment = equipment.find(item => item.equipment_id === selectedEquipmentId) || null;

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

  async function loadNotebook(projectId: string) {
    if (!projectId) { setNotebookEntries([]); return; }
    const result = await api<ListResponse<NotebookEntry>>(`/api/labs/projects/${projectId}/notebook?limit=100`);
    setNotebookEntries(result.items || []);
  }

  async function loadEquipment() {
    const [result, summary] = await Promise.all([
      api<ListResponse<Equipment>>("/api/labs/equipment?limit=100"),
      api<EquipmentSummary>("/api/labs/equipment/summary"),
    ]);
    setEquipment(result.items || []);
    setEquipmentSummary(summary);
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
    setNotebookExperimentId("");
    if (!selectedProjectId) { setExperiments([]); setNotebookEntries([]); return; }
    Promise.all([loadExperiments(selectedProjectId), loadNotebook(selectedProjectId)]).catch(err => {
      setError(true); setMessage(err instanceof Error ? err.message : "Could not load experiments.");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProjectId]);


  useEffect(() => {
    if (!selectedEquipmentId) { setCalibrations([]); setMaintenanceRecords([]); setBookings([]); return; }
    loadEquipmentHistory(selectedEquipmentId).catch(err => {
      setError(true); setMessage(err instanceof Error ? err.message : "Could not load equipment history.");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedEquipmentId]);

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

  async function createNotebookEntry(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProjectId || !notebookTitle.trim() || !notebookContent.trim()) return;
    setBusy(true); setError(false); setMessage("Saving notebook entry…");
    try {
      await api<NotebookEntry>(`/api/labs/projects/${selectedProjectId}/notebook`, {
        method: "POST",
        body: JSON.stringify({ entry_type: notebookType, title: notebookTitle, content: notebookContent, experiment_id: notebookExperimentId || null }),
      });
      setNotebookTitle(""); setNotebookContent("");
      await loadNotebook(selectedProjectId);
      setMessage("Notebook entry saved to the append-only project record.");
    } catch (err) {
      setError(true); setMessage(err instanceof Error ? err.message : "Notebook entry could not be saved.");
    } finally { setBusy(false); }
  }


  async function loadEquipmentHistory(equipmentId: string) {
    if (!equipmentId) { setCalibrations([]); setMaintenanceRecords([]); setBookings([]); return; }
    const [cal, maint, book] = await Promise.all([
      api<ListResponse<Calibration>>(`/api/labs/equipment/${equipmentId}/calibrations?limit=100`),
      api<ListResponse<MaintenanceRecord>>(`/api/labs/equipment/${equipmentId}/maintenance?limit=100`),
      api<ListResponse<EquipmentBooking>>(`/api/labs/equipment/${equipmentId}/bookings?limit=100`),
    ]);
    setCalibrations(cal.items || []);
    setMaintenanceRecords(maint.items || []);
    setBookings(book.items || []);
  }

  async function setEquipmentStatus(nextStatus: string) {
    if (!selectedEquipmentId) return;
    setBusy(true); setError(false);
    try {
      await api(`/api/labs/equipment/${selectedEquipmentId}`, { method: "PATCH", body: JSON.stringify({ status: nextStatus }) });
      await loadEquipment();
      setMessage(`Equipment status changed to ${nextStatus}.`);
    } catch (err) { setError(true); setMessage(err instanceof Error ? err.message : "Equipment status update failed."); }
    finally { setBusy(false); }
  }

  async function addCalibration(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!selectedEquipmentId) return;
    setBusy(true); setError(false);
    try {
      await api(`/api/labs/equipment/${selectedEquipmentId}/calibrations`, { method: "POST", body: JSON.stringify({ calibrated_on: calibrationDate, due_on: calibrationDueDate || null, outcome: calibrationOutcome, performed_by: calibrationPerformer, certificate_reference: calibrationCertificate || null }) });
      setCalibrationDate(""); setCalibrationDueDate(""); setCalibrationPerformer(""); setCalibrationCertificate("");
      await loadEquipmentHistory(selectedEquipmentId); setMessage("Calibration record added.");
    } catch (err) { setError(true); setMessage(err instanceof Error ? err.message : "Calibration record could not be saved."); }
    finally { setBusy(false); }
  }

  async function addMaintenance(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!selectedEquipmentId) return;
    setBusy(true); setError(false);
    try {
      await api(`/api/labs/equipment/${selectedEquipmentId}/maintenance`, { method: "POST", body: JSON.stringify({ maintenance_type: maintenanceType, description: maintenanceDescription, performed_by: maintenancePerformer, performed_at: new Date(maintenancePerformedAt).toISOString(), next_due_at: maintenanceNextDue ? new Date(maintenanceNextDue).toISOString() : null }) });
      setMaintenanceDescription(""); setMaintenancePerformer(""); setMaintenancePerformedAt(""); setMaintenanceNextDue("");
      await loadEquipmentHistory(selectedEquipmentId); setMessage("Maintenance record added.");
    } catch (err) { setError(true); setMessage(err instanceof Error ? err.message : "Maintenance record could not be saved."); }
    finally { setBusy(false); }
  }

  async function createBooking(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!selectedEquipmentId) return;
    setBusy(true); setError(false);
    try {
      await api(`/api/labs/equipment/${selectedEquipmentId}/bookings`, { method: "POST", body: JSON.stringify({ purpose: bookingPurpose, booked_by: bookingBy, starts_at: new Date(bookingStart).toISOString(), ends_at: new Date(bookingEnd).toISOString() }) });
      setBookingPurpose(""); setBookingBy(""); setBookingStart(""); setBookingEnd("");
      await loadEquipmentHistory(selectedEquipmentId); setMessage("Equipment booking confirmed.");
    } catch (err) { setError(true); setMessage(err instanceof Error ? err.message : "Booking could not be created."); }
    finally { setBusy(false); }
  }

  async function updateBooking(bookingId: string, nextStatus: "cancelled" | "completed") {
    setBusy(true); setError(false);
    try {
      await api(`/api/labs/equipment/bookings/${bookingId}`, { method: "PATCH", body: JSON.stringify({ status: nextStatus }) });
      await loadEquipmentHistory(selectedEquipmentId); setMessage(`Booking ${nextStatus}.`);
    } catch (err) { setError(true); setMessage(err instanceof Error ? err.message : "Booking update failed."); }
    finally { setBusy(false); }
  }

  async function registerEquipment(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!equipmentName.trim()) return;
    setBusy(true); setError(false); setMessage("Registering equipment…");
    try {
      const created = await api<Equipment>("/api/labs/equipment", {
        method: "POST",
        body: JSON.stringify({ name: equipmentName, category: equipmentCategory, asset_tag: equipmentAssetTag || null, location: equipmentLocation || null }),
      });
      setEquipmentName(""); setEquipmentAssetTag(""); setEquipmentLocation("");
      setSelectedEquipmentId(created.equipment_id);
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


      <section className="equipment-manager-panel" aria-label="Equipment management">
        <div className="workspace-section-heading"><div><p className="eyebrow">03 · EQUIPMENT MANAGEMENT</p><h2>Calibration, maintenance and bookings</h2></div></div>
        <form className="equipment-register-form" onSubmit={registerEquipment}>
          <label htmlFor="lab-equipment-name">Equipment name</label>
          <input id="lab-equipment-name" value={equipmentName} onChange={e => setEquipmentName(e.target.value)} maxLength={160} required />
          <label htmlFor="lab-equipment-category">Category</label>
          <select id="lab-equipment-category" value={equipmentCategory} onChange={e => setEquipmentCategory(e.target.value)}>
            {["electronics","compute","robotics","mechanical","optical","telecommunications","materials","energy","environmental","other"].map(item => <option key={item}>{item}</option>)}
          </select>
          <label htmlFor="lab-equipment-asset-tag">Asset tag (optional)</label>
          <input id="lab-equipment-asset-tag" value={equipmentAssetTag} onChange={e => setEquipmentAssetTag(e.target.value)} maxLength={100} />
          <label htmlFor="lab-equipment-location">Location (optional)</label>
          <input id="lab-equipment-location" value={equipmentLocation} onChange={e => setEquipmentLocation(e.target.value)} maxLength={200} />
          <button className="primary-button" type="submit" disabled={busy || !equipmentName.trim()}>Register equipment</button>
        </form>
        {equipmentSummary && <div className="equipment-metrics" aria-label="Equipment metrics">
          {[[ "Total assets", equipmentSummary.total_assets ], [ "Available", equipmentSummary.available_assets ], [ "In use", equipmentSummary.in_use_assets ], [ "In maintenance", equipmentSummary.maintenance_assets ], [ "Calibration attention", equipmentSummary.calibration_attention_assets ], [ "Active bookings", equipmentSummary.active_bookings ], [ "Maintenance due in 30 days", equipmentSummary.maintenance_due_30_days ], [ "Overdue maintenance", equipmentSummary.overdue_maintenance_assets ]].map(([label,value]) => <div className="equipment-metric" key={String(label)}><span>{label}</span><strong>{value}</strong></div>)}
        </div>}
        <div className="equipment-manager-layout">
          <div className="lab-list" aria-label="Select an equipment asset">
            {equipment.length === 0 ? <p className="muted">Register an equipment asset to manage its lifecycle.</p> : equipment.map(item =>
              <button type="button" key={item.equipment_id} className={item.equipment_id === selectedEquipmentId ? "lab-list-item selected" : "lab-list-item"} onClick={() => setSelectedEquipmentId(item.equipment_id)}>
                <strong>{item.name}</strong><span>{item.category} · {item.status}{item.asset_tag ? ` · ${item.asset_tag}` : ""}</span>
              </button>)}
          </div>
          {selectedEquipment ? <div className="equipment-detail">
            <div className="equipment-status-row"><h3>{selectedEquipment.name}</h3><label htmlFor="equipment-status">Asset status</label>
              <select id="equipment-status" value={selectedEquipment.status} onChange={e => setEquipmentStatus(e.target.value)} disabled={busy}>
                {["available","in_use","maintenance","retired"].map(value => <option key={value} value={value}>{value.replace("_"," ")}</option>)}
              </select>
            </div>
            <div className="equipment-manager-grid">
              <section className="equipment-subpanel"><h3>Calibration</h3>
                <form className="research-form" onSubmit={addCalibration}>
                  <label htmlFor="calibration-date">Calibration date</label><input id="calibration-date" type="date" value={calibrationDate} onChange={e => setCalibrationDate(e.target.value)} required />
                  <label htmlFor="calibration-due">Next due date</label><input id="calibration-due" type="date" value={calibrationDueDate} onChange={e => setCalibrationDueDate(e.target.value)} />
                  <label htmlFor="calibration-outcome">Outcome</label><select id="calibration-outcome" value={calibrationOutcome} onChange={e => setCalibrationOutcome(e.target.value)}><option value="pass">Pass</option><option value="fail">Fail</option><option value="conditional">Conditional</option></select>
                  <label htmlFor="calibration-performer">Performed by</label><input id="calibration-performer" value={calibrationPerformer} onChange={e => setCalibrationPerformer(e.target.value)} required />
                  <label htmlFor="calibration-certificate">Certificate reference</label><input id="calibration-certificate" value={calibrationCertificate} onChange={e => setCalibrationCertificate(e.target.value)} maxLength={1000} />
                  <button className="primary-button" type="submit" disabled={busy || !calibrationDate || !calibrationPerformer.trim()}>Add calibration</button>
                </form>
                <div className="lab-list">{calibrations.map(item => <div className="lab-list-item" key={item.calibration_id}><strong>{item.outcome.toUpperCase()} · {item.calibrated_on}</strong><span>By {item.performed_by} · Next due: {item.due_on || "Not specified"}</span>{item.certificate_reference && <span>Certificate: {item.certificate_reference}</span>}</div>)}</div>
              </section>
              <section className="equipment-subpanel"><h3>Maintenance</h3>
                <form className="research-form" onSubmit={addMaintenance}>
                  <label htmlFor="maintenance-type">Maintenance type</label><select id="maintenance-type" value={maintenanceType} onChange={e => setMaintenanceType(e.target.value)}>{["preventive","corrective","inspection","repair","other"].map(value => <option key={value}>{value}</option>)}</select>
                  <label htmlFor="maintenance-description">Work performed</label><textarea id="maintenance-description" rows={3} maxLength={4000} value={maintenanceDescription} onChange={e => setMaintenanceDescription(e.target.value)} required />
                  <label htmlFor="maintenance-performer">Performed by</label><input id="maintenance-performer" value={maintenancePerformer} onChange={e => setMaintenancePerformer(e.target.value)} required />
                  <label htmlFor="maintenance-performed-at">Performed at</label><input id="maintenance-performed-at" type="datetime-local" value={maintenancePerformedAt} onChange={e => setMaintenancePerformedAt(e.target.value)} required />
                  <label htmlFor="maintenance-next-due">Next due (optional)</label><input id="maintenance-next-due" type="datetime-local" value={maintenanceNextDue} onChange={e => setMaintenanceNextDue(e.target.value)} />
                  <button className="primary-button" type="submit" disabled={busy || !maintenanceDescription.trim() || !maintenancePerformer.trim() || !maintenancePerformedAt}>Add maintenance</button>
                </form>
                <div className="lab-list">{maintenanceRecords.map(item => <div className="lab-list-item" key={item.maintenance_id}><strong>{item.maintenance_type} · {new Date(item.performed_at).toLocaleString()}</strong><span>{item.description}</span><span>By {item.performed_by} · Next due: {item.next_due_at ? new Date(item.next_due_at).toLocaleString() : "Not specified"}</span></div>)}</div>
              </section>
              <section className="equipment-subpanel"><h3>Booking schedule</h3>
                <form className="research-form" onSubmit={createBooking}>
                  <label htmlFor="booking-purpose">Booking purpose</label><input id="booking-purpose" value={bookingPurpose} onChange={e => setBookingPurpose(e.target.value)} maxLength={1000} required />
                  <label htmlFor="booking-by">Booked by</label><input id="booking-by" value={bookingBy} onChange={e => setBookingBy(e.target.value)} maxLength={160} required />
                  <label htmlFor="booking-start">Starts</label><input id="booking-start" type="datetime-local" value={bookingStart} onChange={e => setBookingStart(e.target.value)} required />
                  <label htmlFor="booking-end">Ends</label><input id="booking-end" type="datetime-local" value={bookingEnd} onChange={e => setBookingEnd(e.target.value)} required />
                  <button className="primary-button" type="submit" disabled={busy || !bookingPurpose.trim() || !bookingBy.trim() || !bookingStart || !bookingEnd}>Reserve equipment</button>
                </form>
                <div className="lab-list">{bookings.map(item => <div className="lab-list-item" key={item.booking_id}><strong>{item.status.toUpperCase()} · {new Date(item.starts_at).toLocaleString()}</strong><span>{item.purpose}</span><span>Until {new Date(item.ends_at).toLocaleString()} · {item.booked_by}</span>{item.status === "confirmed" && <div className="lab-actions"><button className="secondary-button" disabled={busy} onClick={() => updateBooking(item.booking_id,"cancelled")}>Cancel</button><button className="secondary-button" disabled={busy} onClick={() => updateBooking(item.booking_id,"completed")}>Complete</button></div>}</div>)}</div>
              </section>
            </div>
          </div> : <p className="muted">Select an equipment asset to manage calibration, maintenance and bookings.</p>}
        </div>
      </section>

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
            <div className="notebook-panel">
              <p className="eyebrow">DIGITAL RESEARCH NOTEBOOK</p>
              <h3>Record research evidence</h3>
              <form className="research-form" onSubmit={createNotebookEntry}>
                <label htmlFor="lab-notebook-type">Entry type</label>
                <select id="lab-notebook-type" value={notebookType} onChange={e => setNotebookType(e.target.value)}>
                  {["note","hypothesis","observation","measurement","result","decision","protocol","review","deviation"].map(item => <option key={item} value={item}>{item}</option>)}
                </select>
                <label htmlFor="lab-notebook-experiment">Link to experiment (optional)</label>
                <select id="lab-notebook-experiment" value={notebookExperimentId} onChange={e => setNotebookExperimentId(e.target.value)}>
                  <option value="">Project-level entry</option>
                  {experiments.map(item => <option key={item.experiment_id} value={item.experiment_id}>{item.title}</option>)}
                </select>
                <label htmlFor="lab-notebook-title">Entry title</label>
                <input id="lab-notebook-title" value={notebookTitle} onChange={e => setNotebookTitle(e.target.value)} maxLength={180} required />
                <label htmlFor="lab-notebook-content">Observation, method, result or decision</label>
                <textarea id="lab-notebook-content" value={notebookContent} onChange={e => setNotebookContent(e.target.value)} rows={5} maxLength={20000} required />
                <button className="primary-button" type="submit" disabled={busy || !notebookTitle.trim() || !notebookContent.trim()}>Add notebook entry</button>
              </form>
              <div className="lab-list" aria-label="Research notebook timeline">
                {notebookEntries.length === 0 ? <p className="muted">No notebook entries recorded for this project.</p> : notebookEntries.map(entry =>
                  <div className="lab-list-item" key={entry.entry_id}>
                    <strong>{entry.title}</strong><span>{entry.entry_type} · {new Date(entry.created_at).toLocaleString()}</span>
                    <p>{entry.content}</p>
                  </div>)}
              </div>
            </div>
          </> : <p className="muted">Create or select a project to register experiment plans.</p>}
        </article>

      </section>
      <LabInventoryPanel />
    </div>
  );
}
