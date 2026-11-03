"use client";

import { useState } from "react";

type AgentRun = { run_id:string; question:string; status:string; started_at:string; completed_at:string|null };
type AgentResult = { run_id:string; status:string; plan:string[]; summary?:string; sources?:Array<{id:string;title:string;url:string;provider:string;snippet:string}>; citations?:Array<{id:string;title:string;url:string}>; candidate_extraction?:{status:string;candidates_submitted:number;documents_considered:number}; invalid_citations?:string[]; limitations?:string[] };

export default function AutonomousResearchPanel() {
  const [question,setQuestion]=useState("");
  const [extract,setExtract]=useState(false);
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState("An agent can break a research question into focused searches, compare evidence and prepare a cited brief.");
  const [result,setResult]=useState<AgentResult|null>(null);
  const [history,setHistory]=useState<AgentRun[]>([]);
  async function start(event:React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if(question.trim().length<8)return;
    setBusy(true);setMessage("The agent is planning research questions and retrieving sources…");setResult(null);
    try {
      const response=await fetch("/api/research/agent-runs",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json","Accept":"application/json"},body:JSON.stringify({question:question.trim(),max_sources:12,extract_graph_candidates:extract})});
      const queued=await response.json();
      if(!response.ok)throw new Error(queued.detail?.code||queued.error||"Research agent request failed");
      setMessage("Research queued. Waiting for a background worker…");
      let completed:any=null;
      for(let attempt=0;attempt<90;attempt++){
        await new Promise(resolve=>setTimeout(resolve,2000));
        const poll=await fetch("/api/research/agent-runs/"+queued.run_id,{credentials:"same-origin",cache:"no-store"});
        if(!poll.ok)continue;
        const current=await poll.json();
        if(["completed","partial","failed","cancelled"].includes(current.status)){completed=current;break;}
        setMessage("Research agent running · "+current.status+" · "+(attempt+1)*2+" seconds elapsed");
      }
      if(!completed)throw new Error("Research is still running. Its run ID is "+queued.run_id+"; check previous runs shortly.");
      if(completed.status==="failed")throw new Error(completed.error_code||"Research run failed");
      const data={run_id:completed.run_id,status:completed.status,...(completed.result||{}),plan:completed.plan||[]};
      setResult(data);setMessage(data.status==="completed"?"Research run completed. Review the evidence and citations below.":"Research run completed with limitations. Inspect the output carefully.");
      await loadHistory();
    } catch(error){setMessage(error instanceof Error?error.message:"Research agent unavailable");}
    finally{setBusy(false);}
  }
  async function loadHistory(){
    try{const response=await fetch("/api/research/agent-runs?limit=10",{credentials:"same-origin",cache:"no-store"});if(response.ok){const data=await response.json();setHistory(data.items||[]);}}catch{/* history remains optional */}
  }
  async function openRun(id:string){
    try{const response=await fetch("/api/research/agent-runs/"+id,{credentials:"same-origin",cache:"no-store"});const data=await response.json();if(!response.ok)throw new Error(data.detail?.code||"Unable to load run");setResult({run_id:data.run_id,status:data.status,...(data.result||{}),plan:data.plan||[]});setMessage("Loaded saved research run.");}catch(error){setMessage(error instanceof Error?error.message:"Unable to load run");}
  }
  return <section className="agent-research-panel" aria-labelledby="agent-research-title">
    <div className="workspace-section-heading"><div><p className="eyebrow">AUTONOMOUS RESEARCH</p><h2 id="agent-research-title">Research agent</h2></div><span className="count-pill">Human supervised</span></div>
    <p>Give ORIOM7 a research objective. The agent creates a bounded plan, searches configured sources, deduplicates results and prepares a synthesis with source references.</p>
    <form className="agent-research-form" onSubmit={start}>
      <label htmlFor="agent-question">Research objective</label>
      <textarea id="agent-question" rows={3} maxLength={2000} value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Example: Map the leading companies, technologies and investment trends in grid-scale battery storage."/>
      <label className="agent-extraction-option"><input type="checkbox" checked={extract} onChange={e=>setExtract(e.target.checked)}/> Also extract candidate graph relationships from up to five eligible ORIOM7-indexed sources and submit them for human review.</label>
      <div className="research-form-footer"><span className="muted">Maximum 4 plan questions · 12 sources</span><button className="primary-button" type="submit" disabled={busy||question.trim().length<8}>{busy?"Agent working…":"Start research agent"}</button></div>
    </form>
    <p className="status" role="status" aria-live="polite">{message}</p>
    {result&&<div className="agent-result">
      <h3>Research output</h3><p><strong>Run:</strong> {result.run_id} · <strong>Status:</strong> {result.status}</p>
      <h4>Research plan</h4><ol>{(result.plan||[]).map((q,i)=><li key={i}>{q}</li>)}</ol>
      <h4>Research synthesis</h4><div className="research-answer">{result.summary||"No synthesis returned."}</div>
      <h4>Retrieved sources ({result.sources?.length||0})</h4>
      <ol className="agent-source-list">{(result.sources||[]).map(source=><li key={source.id}><a href={source.url} target="_blank" rel="noreferrer"><strong>[{source.id}] {source.title}</strong></a><small>{source.provider}</small><p>{source.snippet}</p></li>)}</ol>
      {result.invalid_citations&&result.invalid_citations.length>0&&<p className="agent-warning">Citation labels requiring validation: {result.invalid_citations.join(", ")}</p>}
      {result.candidate_extraction&&<p><strong>Graph candidate extraction:</strong> {result.candidate_extraction.status}; {result.candidate_extraction.candidates_submitted} candidate(s) submitted for human review.</p>}
      {result.limitations&&<ul>{result.limitations.map((item,i)=><li key={i}>{item}</li>)}</ul>}
    </div>}
    <div className="agent-history"><div className="workspace-section-heading"><h3>Previous runs</h3><button className="secondary-button" type="button" onClick={()=>void loadHistory()}>Refresh history</button></div>
      {history.length===0?<p className="muted">Run history appears here after you load it or complete an investigation.</p>:<ul>{history.map(item=><li key={item.run_id}><button type="button" onClick={()=>void openRun(item.run_id)}>{item.question}</button><small>{item.status} · {new Date(item.started_at).toLocaleString()}</small></li>)}</ul>}
    </div>
    <p className="research-disclaimer">Runs are initiated by you and bounded in scope. The current implementation executes synchronously within the API request; it is not yet a continuously running or scheduled agent service. Candidate graph assertions are never automatically accepted.</p>
  </section>;
}
