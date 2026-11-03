import { useEffect,useState } from "react";
import { api } from "./api";
import { money } from "./formatters";
type Row=Record<string,any>;
type Props={schoolId:number;currency:string;periods:Row[];categories:Row[];canWrite:boolean};
export default function BudgetPanel({schoolId,currency,periods,categories,canWrite}:Props){
 const base=`/api/schools/${schoolId}/expenses/budgets/`;
 const [rows,setRows]=useState<Row[]>([]),[period,setPeriod]=useState(""),[category,setCategory]=useState(""),[amount,setAmount]=useState(""),[notes,setNotes]=useState(""),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 async function refresh(){setRows(await api<Row[]>(base+(period?"?period="+period:"")));}
 useEffect(()=>{void refresh().catch(e=>setError(e.message));},[schoolId,period]);
 async function save(e:React.FormEvent){e.preventDefault();setBusy(true);setError("");try{await api(base,{method:"POST",body:JSON.stringify({period:Number(period),category:Number(category),budget_amount:amount,notes})});setCategory("");setAmount("");setNotes("");await refresh();}catch(err){setError(err instanceof Error?err.message:"Could not save budget.");}finally{setBusy(false);}}
 const totalBudget=rows.reduce((n,r)=>n+Number(r.budget_amount||0),0),totalActual=rows.reduce((n,r)=>n+Number(r.actual_amount||0),0);
 return <section className="data-panel"><div className="panel-heading"><div><h2>Budgets & variance monitoring</h2><p>Set expenditure limits by financial period and expense category, then compare posted expenses and supplier bills.</p></div><button className="secondary" onClick={()=>void refresh()}>Refresh</button></div>
 {error&&<div className="error-banner">{error}</div>}
 <div className="report-controls"><label>Financial period<select value={period} onChange={e=>setPeriod(e.target.value)}><option value="">All periods</option>{periods.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label></div>
 {canWrite&&<form className="entry-panel" onSubmit={save}><h3>Create category budget</h3><div className="form-grid">
  <label>Period<select required value={period} onChange={e=>setPeriod(e.target.value)}><option value="">Select period</option>{periods.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
  <label>Expense category<select required value={category} onChange={e=>setCategory(e.target.value)}><option value="">Select category</option>{categories.filter(c=>c.is_active).map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
  <label>Budget amount<input type="number" min="0" step="0.01" required value={amount} onChange={e=>setAmount(e.target.value)}/></label>
  <label>Notes<input value={notes} onChange={e=>setNotes(e.target.value)}/></label>
 </div><button className="primary" disabled={busy||!period||!category}>{busy?"Saving…":"Save budget"}</button></form>}
 <div className="metric-grid"><div className="metric"><span>Total budget</span><strong>{money(totalBudget,currency)}</strong></div><div className="metric"><span>Actual expenditure</span><strong>{money(totalActual,currency)}</strong></div><div className="metric"><span>Available / (overspend)</span><strong>{money(totalBudget-totalActual,currency)}</strong></div></div>
 <div className="entry-panel"><h3>Budget performance</h3><div className="table-wrap"><table><thead><tr><th>Period</th><th>Category</th><th>Budget</th><th>Actual</th><th>Variance</th><th>Utilisation</th></tr></thead><tbody>{rows.map(r=><tr key={r.id}><td>{r.period_name}</td><td>{r.category_name}</td><td>{money(r.budget_amount,currency)}</td><td>{money(r.actual_amount,currency)}</td><td>{money(r.variance,currency)}</td><td>{r.utilisation_percent==null?"—":r.utilisation_percent+"%"}</td></tr>)}</tbody></table>{!rows.length&&<p className="muted">No budgets configured for this period.</p>}</div></div>
 </section>;
}
