"use client";

import { useCallback, useEffect, useState } from "react";

type Row = Record<string, unknown>;
type List = { items: Row[]; total: number };
type Analytics = { by_currency: Row[]; budgets: Row[]; project_costs: Row[]; currency_policy: string };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, credentials: "same-origin", cache: "no-store",
    headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}), ...init?.headers } });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data?.detail?.code || data?.detail?.message || data?.error || `Request failed (${response.status})`);
  return data as T;
}

export default function LabFinancePanel({ projectId }: { projectId: string }) {
  const [budgets, setBudgets] = useState<List>({ items: [], total: 0 });
  const [grants, setGrants] = useState<List>({ items: [], total: 0 });
  const [transactions, setTransactions] = useState<List>({ items: [], total: 0 });
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [budgetName, setBudgetName] = useState("");
  const [budgetAmount, setBudgetAmount] = useState("");
  const [budgetCurrency, setBudgetCurrency] = useState("GBP");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [expenseDescription, setExpenseDescription] = useState("");
  const [expenseCategory, setExpenseCategory] = useState("consumables");
  const [expenseAmount, setExpenseAmount] = useState("");
  const [expenseCurrency, setExpenseCurrency] = useState("GBP");
  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().slice(0, 10));
  const [recordedBy, setRecordedBy] = useState("");
  const [funder, setFunder] = useState("");
  const [grantAmount, setGrantAmount] = useState("");
  const [grantCurrency, setGrantCurrency] = useState("GBP");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Loading financial records…");
  const [error, setError] = useState(false);

  const refresh = useCallback(async () => {
    const [b, g, t, a] = await Promise.all([
      request<List>("/api/labs/finance/budgets"),
      request<List>("/api/labs/finance/grants"),
      request<List>(`/api/labs/finance/transactions${projectId ? `?project_id=${projectId}` : ""}`),
      request<Analytics>("/api/labs/finance/analytics"),
    ]);
    setBudgets(b); setGrants(g); setTransactions(t); setAnalytics(a);
  }, [projectId]);

  useEffect(() => { refresh().then(() => setMessage("Financial records loaded.")).catch(e => { setError(true); setMessage(e instanceof Error ? e.message : "Could not load finance records."); }); }, [refresh]);

  async function submit(path: string, payload: Row, success: string) {
    setBusy(true); setError(false); setMessage("Saving financial record…");
    try { await request(path, { method: "POST", body: JSON.stringify(payload) }); await refresh(); setMessage(success); }
    catch (e) { setError(true); setMessage(e instanceof Error ? e.message : "Could not save financial record."); }
    finally { setBusy(false); }
  }

  return <section className="research-search-card" aria-label="LAB financial management">
    <p className="eyebrow">06 · FINANCIAL MANAGEMENT & PROJECT COSTING</p>
    <h2>Research finance</h2>
    <p className="muted">Record budgets, funding and project costs. Management information only—not statutory accounts, verified grant claims or tax reporting.</p>
    <div className="lab-metrics">
      {(analytics?.by_currency || []).map(row => <article className="lab-metric" key={String(row.currency)}>
        <strong>{String(row.currency)} {Number(row.net_spend || 0).toLocaleString(undefined,{maximumFractionDigits:2})}</strong><span>Net recorded spend · {String(row.transaction_count)} entries</span>
      </article>)}
    </div>
    <div className="notebook-panel">
      <h3>Create project budget</h3>
      <form className="research-form" onSubmit={e => { e.preventDefault(); void submit("/api/labs/finance/budgets", { project_id: projectId || null, name: budgetName, period_start: periodStart, period_end: periodEnd, currency: budgetCurrency, approved_amount: budgetAmount, status: "draft" }, "Budget recorded."); setBudgetName(""); }}>
        <label>Budget name</label><input value={budgetName} onChange={e=>setBudgetName(e.target.value)} required maxLength={160}/>
        <label>Approved / planned amount</label><input type="number" min="0" step="0.0001" value={budgetAmount} onChange={e=>setBudgetAmount(e.target.value)} required/>
        <label>Currency</label><input value={budgetCurrency} onChange={e=>setBudgetCurrency(e.target.value.toUpperCase())} minLength={3} maxLength={3} required/>
        <label>Period start</label><input type="date" value={periodStart} onChange={e=>setPeriodStart(e.target.value)} required/>
        <label>Period end</label><input type="date" value={periodEnd} onChange={e=>setPeriodEnd(e.target.value)} required/>
        <button className="primary-button" type="submit" disabled={busy || !budgetName.trim() || !budgetAmount}>Save budget</button>
      </form>
    </div>
    <div className="notebook-panel">
      <h3>Record grant or funding award</h3>
      <form className="research-form" onSubmit={e=>{e.preventDefault(); void submit("/api/labs/finance/grants",{project_id:projectId || null,funder_name:funder,currency:grantCurrency,awarded_amount:grantAmount,status:"prospective"},"Funding record saved.");setFunder("");}}>
        <label>Funder / programme</label><input value={funder} onChange={e=>setFunder(e.target.value)} required maxLength={180}/>
        <label>Amount</label><input type="number" min="0" step="0.0001" value={grantAmount} onChange={e=>setGrantAmount(e.target.value)} required/>
        <label>Currency</label><input value={grantCurrency} onChange={e=>setGrantCurrency(e.target.value.toUpperCase())} minLength={3} maxLength={3} required/>
        <button className="primary-button" type="submit" disabled={busy || !funder.trim() || !grantAmount}>Add funding record</button>
      </form>
    </div>
    <div className="notebook-panel">
      <h3>Record project expenditure</h3>
      <form className="research-form" onSubmit={e=>{e.preventDefault();void submit("/api/labs/finance/transactions",{project_id:projectId || null,transaction_type:"expense",category:expenseCategory,description:expenseDescription,amount:expenseAmount,currency:expenseCurrency,transaction_date:expenseDate,recorded_by:recordedBy},"Expense recorded in append-only ledger.");setExpenseDescription("");setExpenseAmount("");}}>
        <label>Expense category</label><select value={expenseCategory} onChange={e=>setExpenseCategory(e.target.value)}>{["consumables","equipment","software","cloud_compute","contractor","travel","facilities","testing","other"].map(x=><option key={x}>{x}</option>)}</select>
        <label>Description</label><input value={expenseDescription} onChange={e=>setExpenseDescription(e.target.value)} required maxLength={500}/>
        <label>Amount</label><input type="number" min="0.0001" step="0.0001" value={expenseAmount} onChange={e=>setExpenseAmount(e.target.value)} required/>
        <label>Currency</label><input value={expenseCurrency} onChange={e=>setExpenseCurrency(e.target.value.toUpperCase())} minLength={3} maxLength={3} required/>
        <label>Transaction date</label><input type="date" value={expenseDate} onChange={e=>setExpenseDate(e.target.value)} required/>
        <label>Recorded by</label><input value={recordedBy} onChange={e=>setRecordedBy(e.target.value)} required maxLength={160}/>
        <button className="primary-button" type="submit" disabled={busy || !expenseDescription.trim() || !expenseAmount || !recordedBy.trim()}>Record expense</button>
      </form>
    </div>
    <div className="lab-list"><h3>Budgets & actuals</h3>{budgets.items.map(row=><div className="lab-list-item" key={String(row.budget_id)}><strong>{String(row.name)} · {String(row.currency)}</strong><span>Budget {String(row.approved_amount)} · recorded spend {String(row.net_spend)} · {String(row.status)}</span></div>)}</div>
    <div className="lab-list"><h3>Funding register</h3>{grants.items.map(row=><div className="lab-list-item" key={String(row.grant_id)}><strong>{String(row.funder_name)} · {String(row.currency)}</strong><span>Award / planned {String(row.awarded_amount)} · utilisation {String(row.utilised_amount)} · {String(row.status)}</span></div>)}</div>
    <div className="lab-list"><h3>Project transactions</h3>{transactions.items.map(row=><div className="lab-list-item" key={String(row.transaction_id)}><strong>{String(row.transaction_date)} · {String(row.currency)} {String(row.amount)}</strong><span>{String(row.category)} · {String(row.description)}</span></div>)}</div>
    <p className={error ? "error-message" : "muted"} role="status">{message}</p>
    <p className="muted">{analytics?.currency_policy}</p>
  </section>;
}
