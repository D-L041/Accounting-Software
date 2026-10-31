import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { money } from "./formatters";

type Row = Record<string, any>;
type Props = { schoolId: number; currency: string; periods: Row[]; accounts: Row[]; canWrite: boolean; onChanged?: () => void };
const today = () => new Date().toISOString().slice(0, 10);

export default function BankReconciliationPanel({ schoolId, currency, periods, accounts, canWrite, onChanged }: Props) {
  const base = `/api/schools/${schoolId}/ledger`;
  const [statements, setStatements] = useState<Row[]>([]);
  const [journals, setJournals] = useState<Row[]>([]);
  const [account, setAccount] = useState("");
  const [period, setPeriod] = useState("");
  const [start, setStart] = useState(today());
  const [end, setEnd] = useState(today());
  const [opening, setOpening] = useState("0.00");
  const [closing, setClosing] = useState("0.00");
  const [lineDate, setLineDate] = useState(today());
  const [lineDescription, setLineDescription] = useState("");
  const [lineReference, setLineReference] = useState("");
  const [lineAmount, setLineAmount] = useState("");
  const [lines, setLines] = useState<Row[]>([]);
  const [selected, setSelected] = useState("");
  const [match, setMatch] = useState<Record<string,string>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const assetAccounts = accounts.filter(a => a.category === "ASSET" && a.is_active);
  const selectedStatement = statements.find(s => String(s.id) === selected) || statements[0];
  const journalLines = useMemo(() => journals.filter(j => j.posted && String(j.period) === String(selectedStatement?.period)).flatMap(j => (j.lines || []).filter((l:Row) => String(l.account) === String(selectedStatement?.account)).map((l:Row) => ({...l, journal_reference:j.reference, entry_date:j.entry_date, description:l.description || j.description}))), [journals, selectedStatement]);
  async function refresh() {
    const [ss, js] = await Promise.all([
      api<Row[]>(`${base}/bank-statements/`),
      api<Row[]>(`${base}/journals/`),
    ]);
    setStatements(ss); setJournals(js);
    if (!selected && ss[0]) setSelected(String(ss[0].id));
  }
  useEffect(() => { void refresh().catch(e => setError(e.message)); }, [schoolId]);
  async function createStatement(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      const created = await api<Row>(`${base}/bank-statements/`, {method:"POST", body:JSON.stringify({
        account:Number(account), period:Number(period), statement_start:start, statement_end:end,
        opening_balance:opening, closing_balance:closing, lines,
      })});
      setLines([]); setLineDescription(""); setLineReference(""); setLineAmount("");
      await refresh(); setSelected(String(created.id)); onChanged?.();
    } catch(err) { setError(err instanceof Error ? err.message : "Could not create bank statement."); }
    finally { setBusy(false); }
  }
  async function matchLine(statementLineId:number) {
    const journalLineId = match[String(statementLineId)];
    if (!journalLineId) return;
    setBusy(true); setError("");
    try {
      await api(`${base}/bank-statements/${selectedStatement.id}/match-line/`, {method:"POST",body:JSON.stringify({statement_line_id:statementLineId,journal_line_id:Number(journalLineId)})});
      await refresh(); onChanged?.();
    } catch(err) { setError(err instanceof Error ? err.message : "Could not match line."); }
    finally { setBusy(false); }
  }
  async function reconcile() {
    setBusy(true); setError("");
    try { await api(`${base}/bank-statements/${selectedStatement.id}/reconcile/`,{method:"POST",body:JSON.stringify({})}); await refresh(); onChanged?.(); }
    catch(err) { setError(err instanceof Error ? err.message : "Could not reconcile statement."); }
    finally { setBusy(false); }
  }
  return <section className="data-panel">
    <div className="panel-heading"><div><h2>Bank reconciliation</h2><p>Import statement lines, match them to posted cash/bank ledger entries, then reconcile.</p></div><button className="secondary" onClick={()=>void refresh()}>Refresh</button></div>
    {error && <div className="error-banner">{error}</div>}
    {canWrite && <form className="entry-form" onSubmit={createStatement}>
      <h3>New bank statement</h3>
      <div className="form-grid">
        <label>Bank / cash account<select required value={account} onChange={e=>setAccount(e.target.value)}><option value="">Select account</option>{assetAccounts.map(a=><option key={a.id} value={a.id}>{a.code} — {a.name}</option>)}</select></label>
        <label>Financial period<select required value={period} onChange={e=>setPeriod(e.target.value)}><option value="">Select period</option>{periods.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        <label>Statement start<input type="date" required value={start} onChange={e=>setStart(e.target.value)}/></label>
        <label>Statement end<input type="date" required value={end} onChange={e=>setEnd(e.target.value)}/></label>
        <label>Opening balance<input type="number" step="0.01" required value={opening} onChange={e=>setOpening(e.target.value)}/></label>
        <label>Closing balance<input type="number" step="0.01" required value={closing} onChange={e=>setClosing(e.target.value)}/></label>
      </div>
      <h4>Add statement line</h4>
      <div className="form-grid">
        <label>Transaction date<input type="date" value={lineDate} onChange={e=>setLineDate(e.target.value)}/></label>
        <label>Description<input value={lineDescription} onChange={e=>setLineDescription(e.target.value)} required/></label>
        <label>Bank reference<input value={lineReference} onChange={e=>setLineReference(e.target.value)}/></label>
        <label>Amount (+ deposit / − withdrawal)<input type="number" step="0.01" value={lineAmount} onChange={e=>setLineAmount(e.target.value)} required/></label>
      </div>
      <button type="button" className="secondary" disabled={!lineDescription || !lineAmount} onClick={()=>{setLines(old=>[...old,{transaction_date:lineDate,description:lineDescription,reference:lineReference,amount:lineAmount}]);setLineDescription("");setLineReference("");setLineAmount("");}}>Add line ({lines.length})</button>
      {lines.length>0 && <ul>{lines.map((l,i)=><li key={i}>{l.transaction_date} · {l.description} · {money(l.amount,currency)} <button type="button" className="text-button" onClick={()=>setLines(old=>old.filter((_,n)=>n!==i))}>Remove</button></li>)}</ul>}
      <button className="primary" disabled={busy || !account || !period || !lines.length}>{busy?"Saving…":"Save statement"}</button>
    </form>}
    <div className="entry-form">
      <h3>Match statement transactions</h3>
      <label>Statement<select value={selectedStatement?.id || ""} onChange={e=>setSelected(e.target.value)}><option value="">Select statement</option>{statements.map(s=><option key={s.id} value={s.id}>{s.account_name} · ending {s.statement_end} · {s.status}</option>)}</select></label>
      {selectedStatement && <>
        <p>Statement movement: <strong>{money(selectedStatement.statement_movement,currency)}</strong> · Calculated closing: <strong>{money(selectedStatement.calculated_closing_balance,currency)}</strong> · Status: <strong>{selectedStatement.status}</strong></p>
        <div className="table-wrap"><table><thead><tr><th>Date</th><th>Description</th><th>Reference</th><th>Amount</th><th>Ledger match</th><th>Action</th></tr></thead><tbody>
          {(selectedStatement.lines||[]).map((l:Row)=><tr key={l.id}><td>{l.transaction_date}</td><td>{l.description}</td><td>{l.reference||"—"}</td><td>{money(l.amount,currency)}</td><td>{l.matched_journal_reference || <select disabled={!canWrite || selectedStatement.status!=="DRAFT"} value={match[String(l.id)]||""} onChange={e=>setMatch(old=>({...old,[String(l.id)]:e.target.value}))}><option value="">Choose posted ledger line</option>{journalLines.map((j:Row)=><option key={j.id} value={j.id}>{j.journal_reference} · {j.entry_date} · {j.description} · {money(Number(j.debit)-Number(j.credit),currency)}</option>)}</select>}</td><td>{!l.matched_journal_line && canWrite && selectedStatement.status==="DRAFT" && <button className="small-action" disabled={busy||!match[String(l.id)]} onClick={()=>void matchLine(l.id)}>Match</button>}</td></tr>)}
        </tbody></table></div>
        {canWrite && selectedStatement.status==="DRAFT" && <button className="primary" disabled={busy || !(selectedStatement.lines||[]).length || (selectedStatement.lines||[]).some((l:Row)=>!l.matched_journal_line) || !selectedStatement.is_statement_arithmetic_valid} onClick={()=>void reconcile()}>Reconcile statement</button>}
      </>}
    </div>
  </section>;
}
