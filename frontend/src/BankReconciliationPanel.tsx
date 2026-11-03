import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { money } from "./formatters";

type Row = Record<string, any>;
type Props = { schoolId: number; currency: string; periods: Row[]; accounts: Row[]; canWrite: boolean; onChanged?: () => void };
const today = () => new Date().toISOString().slice(0, 10);

function parseCsv(text: string): string[][] {
  const rows: string[][] = []; let row: string[] = []; let cell = ""; let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (char === '"' && quoted && text[i + 1] === '"') { cell += '"'; i += 1; }
    else if (char === '"') quoted = !quoted;
    else if (char === "," && !quoted) { row.push(cell.trim()); cell = ""; }
    else if ((char === "\\n" || char === "\\r") && !quoted) {
      if (char === "\\r" && text[i + 1] === "\\n") i += 1;
      row.push(cell.trim()); if (row.some(value => value !== "")) rows.push(row);
      row = []; cell = "";
    } else cell += char;
  }
  row.push(cell.trim()); if (row.some(value => value !== "")) rows.push(row);
  if (quoted) throw new Error("CSV contains an unfinished quoted field.");
  return rows;
}

function normaliseBankDate(value: string): string {
  const input = value.trim();
  if (/^\\d{4}-\\d{2}-\\d{2}$/.test(input)) return input;
  const match = input.match(/^(\\d{1,2})[\\/.-](\\d{1,2})[\\/.-](\\d{4})$/);
  if (match) return `${match[3]}-${match[2].padStart(2,"0")}-${match[1].padStart(2,"0")}`;
  throw new Error(`Unsupported bank statement date: ${value}. Use YYYY-MM-DD or DD/MM/YYYY.`);
}

function normaliseBankAmount(value: string): string {
  let input = value.trim().replace(/,/g, "").replace(/KES/gi, "").trim();
  const debit = /\\bDR\\b/i.test(input) || /^\\(.*\\)$/.test(input);
  input = input.replace(/\\b(?:DR|CR)\\b/gi, "").replace(/[()\\s]/g, "");
  if (!/^-?\\d+(?:\\.\\d{1,2})?$/.test(input)) throw new Error(`Invalid bank amount: ${value}`);
  const amount = Number(input) * (debit && !input.startsWith("-") ? -1 : 1);
  if (!Number.isFinite(amount) || amount === 0) throw new Error("Bank statement amounts must be non-zero.");
  return amount.toFixed(2);
}

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
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [csvRows, setCsvRows] = useState<string[][]>([]);
  const [csvMapping, setCsvMapping] = useState({date:"",description:"",amount:"",reference:""});
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
  async function loadCsv(file?: File) {
    if (!file) return;
    setError("");
    try {
      const parsed = parseCsv(await file.text());
      if (parsed.length < 2) throw new Error("The CSV must contain a header row and at least one transaction.");
      const headers = parsed[0].map((value,index)=>value || `Column ${index+1}`);
      const find = (pattern:RegExp) => headers.find(header=>pattern.test(header.toLowerCase())) || "";
      setCsvHeaders(headers); setCsvRows(parsed.slice(1));
      setCsvMapping({date:find(/date|posted/),description:find(/description|details|narration|particular/),amount:find(/amount|value/),reference:find(/reference|ref|transaction|cheque/)});
    } catch(err) { setError(err instanceof Error?err.message:"Could not read the CSV file."); }
  }
  function applyCsvRows() {
    try {
      if (!csvMapping.date || !csvMapping.description || !csvMapping.amount) throw new Error("Map date, description and amount columns before importing.");
      const index = (name:string) => csvHeaders.indexOf(name);
      const imported = csvRows.map((row)=>({
        transaction_date:normaliseBankDate(row[index(csvMapping.date)]||""),
        description:(row[index(csvMapping.description)]||"").slice(0,255),
        reference:csvMapping.reference?(row[index(csvMapping.reference)]||"").slice(0,100):"",
        amount:normaliseBankAmount(row[index(csvMapping.amount)]||""),
      }));
      if (imported.some(line=>!line.description)) throw new Error("Every imported bank transaction needs a description.");
      setLines(old=>[...old,...imported]); setCsvHeaders([]); setCsvRows([]);
      setError("");
    } catch(err) { setError(err instanceof Error?err.message:"Could not import CSV rows."); }
  }

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
    {canWrite && <form className="entry-panel" onSubmit={createStatement}>
      <h3>New bank statement</h3>
      <div className="form-grid">
        <label>Bank / cash account<select required value={account} onChange={e=>setAccount(e.target.value)}><option value="">Select account</option>{assetAccounts.map(a=><option key={a.id} value={a.id}>{a.code} — {a.name}</option>)}</select></label>
        <label>Financial period<select required value={period} onChange={e=>setPeriod(e.target.value)}><option value="">Select period</option>{periods.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        <label>Statement start<input type="date" required value={start} onChange={e=>setStart(e.target.value)}/></label>
        <label>Statement end<input type="date" required value={end} onChange={e=>setEnd(e.target.value)}/></label>
        <label>Opening balance<input type="number" step="0.01" required value={opening} onChange={e=>setOpening(e.target.value)}/></label>
        <label>Closing balance<input type="number" step="0.01" required value={closing} onChange={e=>setClosing(e.target.value)}/></label>
      </div>
      <div className="entry-panel"><h3>Import bank statement CSV</h3><p>Upload a CSV and map its columns. Positive values are deposits; negative values or DR amounts are withdrawals.</p><div className="form-grid"><label>CSV file<input type="file" accept=".csv,text/csv" onChange={e=>void loadCsv(e.target.files?.[0])}/></label><label>Template <a href="data:text/csv;charset=utf-8,transaction_date%2Cdescription%2Creference%2Camount%0A2026-10-01%2CExample%20deposit%2CREF001%2C1000.00" download="precious-schoolbooks-bank-import-template.csv">Download CSV template</a></label></div>{csvHeaders.length>0&&<><div className="form-grid"><label>Date column<select value={csvMapping.date} onChange={e=>setCsvMapping(v=>({...v,date:e.target.value}))}><option value="">Select column</option>{csvHeaders.map(h=><option key={h}>{h}</option>)}</select></label><label>Description column<select value={csvMapping.description} onChange={e=>setCsvMapping(v=>({...v,description:e.target.value}))}><option value="">Select column</option>{csvHeaders.map(h=><option key={h}>{h}</option>)}</select></label><label>Amount column<select value={csvMapping.amount} onChange={e=>setCsvMapping(v=>({...v,amount:e.target.value}))}><option value="">Select column</option>{csvHeaders.map(h=><option key={h}>{h}</option>)}</select></label><label>Reference column<select value={csvMapping.reference} onChange={e=>setCsvMapping(v=>({...v,reference:e.target.value}))}><option value="">Not supplied</option>{csvHeaders.map(h=><option key={h}>{h}</option>)}</select></label></div><p>{csvRows.length} CSV transaction row(s) loaded.</p><button type="button" className="secondary" onClick={applyCsvRows}>Add imported rows to statement</button></>}</div>
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
    <div className="entry-panel">
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
