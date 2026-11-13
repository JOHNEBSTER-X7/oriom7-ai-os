"use client";

import { useEffect, useState } from "react";

type Inspection={inspection_id:string;lot_code:string;sku:string;name:string;inspection_type:string;outcome:string;sample_size:number;defects_count:number;performed_by:string;inspected_at:string};
type NCR={nonconformance_id:string;title:string;description:string;severity:string;status:string;assigned_to:string|null;due_date:string|null};
type Capa={action_id:string;nonconformance_id:string;nonconformance_title:string;action_type:string;description:string;assigned_to:string;due_date:string|null;status:string};
type Doc={document_id:string;supplier_name:string|null;document_type:string;document_name:string;reference:string;expires_at:string|null;review_status:string;expiry_state:string};
type Analytics={metrics:{total_inspections:number;passed_inspections:number;failed_inspections:number;conditional_inspections:number;open_nonconformances:number;open_capa_actions:number;overdue_capa_actions:number;documents_pending_review:number;expired_documents:number;documents_expiring_30_days:number};supplier_quality:{supplier_id:string;name:string;inspections:number;passed:number;failed:number;conditional:number;pass_rate_percent:number|null}[]};

async function call<T>(path:string,method="GET",body?:unknown):Promise<T>{
 const response=await fetch(path,{method,credentials:"same-origin",cache:"no-store",headers:{"Accept":"application/json",...(body?{"Content-Type":"application/json"}:{})},...(body?{body:JSON.stringify(body)}:{})});
 const data=await response.json().catch(()=>({}));
 if(!response.ok)throw new Error(data?.detail?.code||data?.detail?.message||data?.error||`Request failed (${response.status})`);
 return data as T;
}

export default function LabQualityPanel(){
 const [inspections,setInspections]=useState<Inspection[]>([]),[ncrs,setNcrs]=useState<NCR[]>([]),[capas,setCapas]=useState<Capa[]>([]),[docs,setDocs]=useState<Doc[]>([]);
 const [analytics,setAnalytics]=useState<Analytics|null>(null),[lots,setLots]=useState<{lot_id:string;lot_code:string;sku:string;name:string}[]>([]),[suppliers,setSuppliers]=useState<{supplier_id:string;name:string}[]>([]);
 const [busy,setBusy]=useState(false),[message,setMessage]=useState("");
 const [lotId,setLotId]=useState(""),[inspectionType,setInspectionType]=useState("Incoming inspection"),[outcome,setOutcome]=useState("pass"),[sampleSize,setSampleSize]=useState("1"),[defects,setDefects]=useState("0"),[performedBy,setPerformedBy]=useState(""),[inspectionNotes,setInspectionNotes]=useState("");
 const [ncrTitle,setNcrTitle]=useState(""),[ncrDescription,setNcrDescription]=useState(""),[severity,setSeverity]=useState("major");
 const [capaNcr,setCapaNcr]=useState(""),[capaType,setCapaType]=useState("corrective"),[capaDescription,setCapaDescription]=useState(""),[capaOwner,setCapaOwner]=useState("");
 const [docSupplier,setDocSupplier]=useState(""),[docType,setDocType]=useState(""),[docName,setDocName]=useState(""),[docRef,setDocRef]=useState(""),[docExpiry,setDocExpiry]=useState("");
 async function load(){
  const [q,n,c,d,a,l,s]=await Promise.all([
   call<{items:Inspection[]}>("/api/labs/quality/inspections"),call<{items:NCR[]}>("/api/labs/quality/nonconformances"),
   call<{items:Capa[]}>("/api/labs/quality/capa"),call<{items:Doc[]}>("/api/labs/quality/compliance-documents"),
   call<Analytics>("/api/labs/quality/analytics"),call<{items:typeof lots}>("/api/labs/inventory/lots"),
   call<{items:typeof suppliers}>("/api/labs/inventory/suppliers")
  ]);
  setInspections(q.items||[]);setNcrs(n.items||[]);setCapas(c.items||[]);setDocs(d.items||[]);setAnalytics(a);setLots(l.items||[]);setSuppliers(s.items||[]);
 }
 useEffect(()=>{load().catch(e=>setMessage(e.message));},[]);
 async function run(fn:()=>Promise<unknown>,done:string){setBusy(true);setMessage("");try{await fn();await load();setMessage(done);}catch(e){setMessage(e instanceof Error?e.message:"Request failed");}finally{setBusy(false);}}
 return <section className="research-search-card inventory-panel" aria-label="Laboratory quality compliance and analytics">
  <p className="eyebrow">05 · QUALITY, COMPLIANCE & ANALYTICS</p><h2>Quality assurance and compliance workspace</h2>
  {analytics&&<div className="equipment-metrics">{[
   ["Inspections",analytics.metrics.total_inspections],["Passed",analytics.metrics.passed_inspections],["Failed",analytics.metrics.failed_inspections],["Conditional",analytics.metrics.conditional_inspections],
   ["Open non-conformances",analytics.metrics.open_nonconformances],["Open CAPA",analytics.metrics.open_capa_actions],
   ["Overdue CAPA",analytics.metrics.overdue_capa_actions],["Documents to review",analytics.metrics.documents_pending_review],
   ["Expired documents",analytics.metrics.expired_documents],["Expiring in 30 days",analytics.metrics.documents_expiring_30_days]
  ].map(([k,v])=><div className="equipment-metric" key={String(k)}><span>{k}</span><strong>{v}</strong></div>)}</div>}
  {message&&<p role="status" className="muted">{message}</p>}
  <div className="equipment-manager-grid">
   <section className="equipment-subpanel"><h3>Record lot inspection</h3><form className="research-form" onSubmit={e=>{e.preventDefault();void run(()=>call("/api/labs/quality/inspections","POST",{lot_id:lotId,inspection_type:inspectionType,outcome,sample_size:Number(sampleSize),defects_count:Number(defects),performed_by:performedBy,notes:inspectionNotes||null}),"Inspection recorded. Failed or conditional lots are quarantined and generate a non-conformance.");}}>
    <label>Batch / lot</label><select value={lotId} onChange={e=>setLotId(e.target.value)} required><option value="">Select lot</option>{lots.map(l=><option key={l.lot_id} value={l.lot_id}>{l.sku} · {l.lot_code} · {l.name}</option>)}</select>
    <label>Inspection type</label><input value={inspectionType} onChange={e=>setInspectionType(e.target.value)} required/>
    <label>Outcome</label><select value={outcome} onChange={e=>setOutcome(e.target.value)}><option value="pass">Pass</option><option value="fail">Fail</option><option value="conditional">Conditional / hold</option></select>
    <label>Sample size</label><input type="number" min="1" value={sampleSize} onChange={e=>setSampleSize(e.target.value)}/>
    <label>Defects observed</label><input type="number" min="0" value={defects} onChange={e=>setDefects(e.target.value)}/>
    <label>Performed by</label><input value={performedBy} onChange={e=>setPerformedBy(e.target.value)} required/>
    <label>Notes / findings</label><textarea value={inspectionNotes} onChange={e=>setInspectionNotes(e.target.value)}/>
    <button className="primary-button" disabled={busy||!lotId||!performedBy.trim()}>Save inspection</button>
   </form></section>
   <section className="equipment-subpanel"><h3>Open non-conformance</h3><form className="research-form" onSubmit={e=>{e.preventDefault();void run(()=>call("/api/labs/quality/nonconformances","POST",{title:ncrTitle,description:ncrDescription,severity}),"Non-conformance opened.");setNcrTitle("");setNcrDescription("");}}>
    <label>Title</label><input value={ncrTitle} onChange={e=>setNcrTitle(e.target.value)} required/><label>Description</label><textarea value={ncrDescription} onChange={e=>setNcrDescription(e.target.value)} required/><label>Severity</label><select value={severity} onChange={e=>setSeverity(e.target.value)}><option value="minor">Minor</option><option value="major">Major</option><option value="critical">Critical</option></select><button className="primary-button" disabled={busy||!ncrTitle.trim()||!ncrDescription.trim()}>Create non-conformance</button>
   </form><div className="lab-list">{ncrs.map(n=><div className="lab-list-item" key={n.nonconformance_id}><strong>{n.severity.toUpperCase()} · {n.status.replaceAll("_"," ")}</strong><span>{n.title}</span></div>)}</div></section>
   <section className="equipment-subpanel"><h3>Corrective / preventive action</h3><form className="research-form" onSubmit={e=>{e.preventDefault();void run(()=>call("/api/labs/quality/capa","POST",{nonconformance_id:capaNcr,action_type:capaType,description:capaDescription,assigned_to:capaOwner,recorded_by:capaOwner}),"CAPA action assigned.");setCapaDescription("");}}>
    <label>Non-conformance</label><select value={capaNcr} onChange={e=>setCapaNcr(e.target.value)} required><option value="">Select case</option>{ncrs.filter(n=>!["closed","verified"].includes(n.status)).map(n=><option key={n.nonconformance_id} value={n.nonconformance_id}>{n.severity} · {n.title}</option>)}</select>
    <label>Action type</label><select value={capaType} onChange={e=>setCapaType(e.target.value)}><option value="correction">Correction</option><option value="corrective">Corrective</option><option value="preventive">Preventive</option></select>
    <label>Action description</label><textarea value={capaDescription} onChange={e=>setCapaDescription(e.target.value)} required/><label>Assigned to</label><input value={capaOwner} onChange={e=>setCapaOwner(e.target.value)} required/><button className="primary-button" disabled={busy||!capaNcr||!capaDescription.trim()||!capaOwner.trim()}>Assign action</button>
   </form><div className="lab-list">{capas.map(a=><div className="lab-list-item" key={a.action_id}><strong>{a.action_type.toUpperCase()} · {a.status}</strong><span>{a.description} · {a.assigned_to}</span>{a.status!=="verified"&&<button className="secondary-button" disabled={busy} onClick={()=>void run(()=>call(`/api/labs/quality/capa/${a.action_id}`,"PATCH",{status:a.status==="planned"?"in_progress":a.status==="in_progress"?"completed":"verified",recorded_by:a.assigned_to}),"CAPA status updated.")}>Advance action</button>}</div>)}</div></section>
   <section className="equipment-subpanel"><h3>Compliance document register</h3><form className="research-form" onSubmit={e=>{e.preventDefault();void run(()=>call("/api/labs/quality/compliance-documents","POST",{supplier_id:docSupplier||null,document_type:docType,document_name:docName,reference:docRef,expires_at:docExpiry||null}),"Document registered for review.");setDocName("");setDocRef("");}}>
    <label>Supplier (optional)</label><select value={docSupplier} onChange={e=>setDocSupplier(e.target.value)}><option value="">Organisation / general</option>{suppliers.map(s=><option key={s.supplier_id} value={s.supplier_id}>{s.name}</option>)}</select>
    <label>Document type</label><input value={docType} onChange={e=>setDocType(e.target.value)} required placeholder="SDS, ISO certificate, permit..."/>
    <label>Document name</label><input value={docName} onChange={e=>setDocName(e.target.value)} required/><label>Reference / storage URI</label><input value={docRef} onChange={e=>setDocRef(e.target.value)} required/><label>Expiry date</label><input type="date" value={docExpiry} onChange={e=>setDocExpiry(e.target.value)}/><button className="primary-button" disabled={busy||!docType.trim()||!docName.trim()||!docRef.trim()}>Register document</button>
   </form><div className="lab-list">{docs.map(d=><div className="lab-list-item" key={d.document_id}><strong>{d.document_type} · {d.review_status.replaceAll("_"," ")}</strong><span>{d.document_name} · {d.supplier_name||"General"} · {d.expiry_state.replaceAll("_"," ")}</span>{d.review_status==="pending_review"&&<><label>Reviewed by</label><input value={reviewedBy} onChange={e=>setReviewedBy(e.target.value)} placeholder="Reviewer name"/><button className="secondary-button" disabled={busy||!reviewedBy.trim()} onClick={()=>void run(()=>call(`/api/labs/quality/compliance-documents/${d.document_id}/review`,"PATCH",{review_status:"accepted",reviewed_by:reviewedBy}),"Document review recorded.")}>Accept document</button><button className="secondary-button" disabled={busy||!reviewedBy.trim()} onClick={()=>void run(()=>call(`/api/labs/quality/compliance-documents/${d.document_id}/review`,"PATCH",{review_status:"rejected",reviewed_by:reviewedBy}),"Document rejection recorded.")}>Reject document</button></>}</div>)}</div></section>
   <section className="equipment-subpanel"><h3>Supplier quality scorecard</h3><div className="lab-list">{analytics?.supplier_quality.map(s=><div className="lab-list-item" key={s.supplier_id}><strong>{s.name}</strong><span>{s.inspections} inspections · {s.passed} passed · {s.failed} failed · {s.conditional} conditional · {s.pass_rate_percent===null?"No scored inspections":`${s.pass_rate_percent}% pass rate`}</span></div>)}</div></section>
   <section className="equipment-subpanel"><h3>Inspection history</h3><div className="lab-list">{inspections.map(i=><div className="lab-list-item" key={i.inspection_id}><strong>{i.outcome.toUpperCase()} · {i.sku} · {i.lot_code}</strong><span>{i.inspection_type} · {i.defects_count}/{i.sample_size} defects · {i.performed_by}</span></div>)}</div></section>
  </div>
  <p className="muted">This is an auditable management record, not a validated QMS, accredited inspection service, legal compliance determination, supplier certification or substitute for competent quality and regulatory review. Evidence references point to records held elsewhere; files are not independently authenticated.</p>
 </section>;
}
