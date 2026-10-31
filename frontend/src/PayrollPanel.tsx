import { useEffect, useState } from "react";
import { api } from "./api";
import { money } from "./formatters";

type Row=Record<string,any>;
type Props={schoolId:number;currency:string;periods:Row[];accounts:Row[];canWrite:boolean;canAdmin:boolean;onChanged?:()=>void};
const today=()=>new Date().toISOString().slice(0,10);
const monthStart=()=>{const d=new Date();return new Date(d.getFullYear(),d.getMonth(),1).toISOString().slice(0,10);};

export default function PayrollPanel({schoolId,currency,periods,accounts,canWrite,canAdmin,onChanged}:Props){
 const base=`/api/schools/${schoolId}/payroll`;
 const [employees,setEmployees]=useState<Row[]>([]);
 const [runs,setRuns]=useState<Row[]>([]);
 const [settings,setSettings]=useState<Row|null>(null);
 const [rules,setRules]=useState<Row[]>([]);
 const [bands,setBands]=useState<Row[]>([]);
 const [employee,setEmployee]=useState({employee_number:"",first_name:"",last_name:"",job_title:"",basic_salary:"",regular_cash_allowances:"0.00",monthly_other_deductions:"0.00",monthly_insurance_premiums:"0.00",monthly_mortgage_interest:"0.00",monthly_post_retirement_medical:"0.00",monthly_additional_pension:"0.00",tax_claims_reference:"",tax_claims_verified:false,tax_exemption_certificate_ref:"",tax_exemption_valid_from:"",tax_exemption_valid_to:"",tax_exemption_verified:false,hire_date:today(),is_resident:true});
 const [period,setPeriod]=useState("");
 const [month,setMonth]=useState(monthStart());
 const [payDate,setPayDate]=useState(today());
 const [mapping,setMapping]=useState<Record<string,string>>({});
 const [error,setError]=useState("");
 const [busy,setBusy]=useState(false);
 const expenses=accounts.filter(a=>a.category==="EXPENSE"&&a.is_active);
 const liabilities=accounts.filter(a=>a.category==="LIABILITY"&&a.is_active);
 async function refresh(){
  const [e,r,s,pr,tb]=await Promise.all([
   api<Row[]>(`${base}/employees/`),api<Row[]>(`${base}/runs/`),
   api<Row[]>(`${base}/settings/`),api<Row[]>(`${base}/rules/`),api<Row[]>(`${base}/tax-bands/`),
  ]);
  setEmployees(e);setRuns(r);setSettings(s[0]||null);setRules(pr);setBands(tb);
  if(s[0])setMapping({salary_expense_account:String(s[0].salary_expense_account),net_payable_account:String(s[0].net_payable_account),paye_payable_account:String(s[0].paye_payable_account),nssf_payable_account:String(s[0].nssf_payable_account),shif_payable_account:String(s[0].shif_payable_account),housing_levy_payable_account:String(s[0].housing_levy_payable_account),other_deductions_payable_account:String(s[0].other_deductions_payable_account),nita_payable_account:s[0].nita_payable_account?String(s[0].nita_payable_account):"",additional_pension_payable_account:s[0].additional_pension_payable_account?String(s[0].additional_pension_payable_account):""});
 }
 useEffect(()=>{void refresh().catch(e=>setError(e.message));},[schoolId]);
 async function createEmployee(e:React.FormEvent){
  e.preventDefault();setBusy(true);setError("");
  try{await api(`${base}/employees/`,{method:"POST",body:JSON.stringify({...employee,tax_exemption_valid_from:employee.tax_exemption_valid_from||null,tax_exemption_valid_to:employee.tax_exemption_valid_to||null})});setEmployee({employee_number:"",first_name:"",last_name:"",job_title:"",basic_salary:"",regular_cash_allowances:"0.00",monthly_other_deductions:"0.00",monthly_insurance_premiums:"0.00",monthly_mortgage_interest:"0.00",monthly_post_retirement_medical:"0.00",monthly_additional_pension:"0.00",tax_claims_reference:"",tax_claims_verified:false,tax_exemption_certificate_ref:"",tax_exemption_valid_from:"",tax_exemption_valid_to:"",tax_exemption_verified:false,hire_date:today(),is_resident:true});await refresh();onChanged?.();}
  catch(err){setError(err instanceof Error?err.message:"Could not add employee.");}finally{setBusy(false);}
 }
 async function saveSettings(e:React.FormEvent){
  e.preventDefault();setBusy(true);setError("");
  try{await api(settings ? `${base}/settings/${settings.id}/` : `${base}/settings/`,{method:settings?"PATCH":"POST",body:JSON.stringify(mapping)});await refresh();onChanged?.();}
  catch(err){setError(err instanceof Error?err.message:"Could not save payroll account mappings.");}finally{setBusy(false);}
 }
 async function createRun(e:React.FormEvent){
  e.preventDefault();setBusy(true);setError("");
  try{await api(`${base}/runs/`,{method:"POST",body:JSON.stringify({period:Number(period),payroll_month:month,pay_date:payDate})});await refresh();onChanged?.();}
  catch(err){setError(err instanceof Error?err.message:"Could not calculate payroll.");}finally{setBusy(false);}
 }
 async function postRun(id:number){
  setBusy(true);setError("");
  try{await api(`${base}/runs/${id}/post/`,{method:"POST",body:JSON.stringify({})});await refresh();onChanged?.();}
  catch(err){setError(err instanceof Error?err.message:"Could not post payroll.");}finally{setBusy(false);}
 }
 return <section className="data-panel">
  <div className="panel-heading"><div><h2>Staff & payroll</h2><p>Maintain employee records, configure ledger mappings, calculate payroll and post approved runs.</p></div><button className="secondary" onClick={()=>void refresh()}>Refresh</button></div>
  {error&&<div className="error-banner">{error}</div>}
  {canWrite&&<div className="setup-grid">
   <form className="entry-panel" onSubmit={createEmployee}>
    <h3>Add employee</h3>
    <label>Employee number<input required value={employee.employee_number} onChange={e=>setEmployee(v=>({...v,employee_number:e.target.value}))}/></label>
    <div className="form-grid"><label>First name<input required value={employee.first_name} onChange={e=>setEmployee(v=>({...v,first_name:e.target.value}))}/></label><label>Last name<input required value={employee.last_name} onChange={e=>setEmployee(v=>({...v,last_name:e.target.value}))}/></label></div>
    <label>Job title<input value={employee.job_title} onChange={e=>setEmployee(v=>({...v,job_title:e.target.value}))}/></label>
    <div className="form-grid"><label>Basic monthly salary<input type="number" min="0" step="0.01" required value={employee.basic_salary} onChange={e=>setEmployee(v=>({...v,basic_salary:e.target.value}))}/></label><label>Regular monthly cash allowances<input type="number" min="0" step="0.01" value={employee.regular_cash_allowances} onChange={e=>setEmployee(v=>({...v,regular_cash_allowances:e.target.value}))}/></label><label>Other monthly deductions<input type="number" min="0" step="0.01" value={employee.monthly_other_deductions} onChange={e=>setEmployee(v=>({...v,monthly_other_deductions:e.target.value}))}/></label><label>Hire date<input type="date" required value={employee.hire_date} onChange={e=>setEmployee(v=>({...v,hire_date:e.target.value}))}/></label></div>
    <details className="entry-panel"><summary>Employee tax claims and exemptions</summary><p className="muted">Enter amounts supported by current documents. Claims are excluded until verified by a school owner or administrator.</p>
     <div className="form-grid">
      <label>Monthly insurance premiums<input type="number" min="0" step="0.01" value={employee.monthly_insurance_premiums} onChange={e=>setEmployee(v=>({...v,monthly_insurance_premiums:e.target.value}))}/></label>
      <label>Monthly mortgage interest<input type="number" min="0" step="0.01" value={employee.monthly_mortgage_interest} onChange={e=>setEmployee(v=>({...v,monthly_mortgage_interest:e.target.value}))}/></label>
      <label>Post-retirement medical fund<input type="number" min="0" step="0.01" value={employee.monthly_post_retirement_medical} onChange={e=>setEmployee(v=>({...v,monthly_post_retirement_medical:e.target.value}))}/></label>
      <label>Additional registered pension<input type="number" min="0" step="0.01" value={employee.monthly_additional_pension} onChange={e=>setEmployee(v=>({...v,monthly_additional_pension:e.target.value}))}/></label>
     </div>
     <label>Supporting document reference<input value={employee.tax_claims_reference} onChange={e=>setEmployee(v=>({...v,tax_claims_reference:e.target.value}))}/></label>
     {canAdmin&&<label className="check-label"><input type="checkbox" checked={employee.tax_claims_verified} onChange={e=>setEmployee(v=>({...v,tax_claims_verified:e.target.checked}))}/> I have checked the supporting documents for these claims</label>}
     <label>Tax exemption certificate reference<input value={employee.tax_exemption_certificate_ref} onChange={e=>setEmployee(v=>({...v,tax_exemption_certificate_ref:e.target.value}))}/></label>
     <div className="form-grid"><label>Certificate valid from<input type="date" value={employee.tax_exemption_valid_from} onChange={e=>setEmployee(v=>({...v,tax_exemption_valid_from:e.target.value}))}/></label><label>Certificate valid to<input type="date" value={employee.tax_exemption_valid_to} onChange={e=>setEmployee(v=>({...v,tax_exemption_valid_to:e.target.value}))}/></label></div>
     {canAdmin&&<label className="check-label"><input type="checkbox" checked={employee.tax_exemption_verified} onChange={e=>setEmployee(v=>({...v,tax_exemption_verified:e.target.checked}))}/> I have authenticated this exemption certificate</label>}
    </details>
    <label className="check-label"><input type="checkbox" checked={employee.is_resident} onChange={e=>setEmployee(v=>({...v,is_resident:e.target.checked}))}/> Resident individual (eligible for personal relief)</label>
    <button className="primary" disabled={busy}>{busy?"Saving…":"Add employee"}</button>
   </form>
   <form className="entry-panel" onSubmit={saveSettings}>
    <h3>Payroll ledger accounts</h3>
    <label>Salary expense<select required value={mapping.salary_expense_account||""} onChange={e=>setMapping(v=>({...v,salary_expense_account:e.target.value}))}><option value="">Select expense account</option>{expenses.map(a=><option key={a.id} value={a.id}>{a.code} — {a.name}</option>)}</select></label>
    {(["net_payable_account","paye_payable_account","nssf_payable_account","shif_payable_account","housing_levy_payable_account","other_deductions_payable_account","nita_payable_account","additional_pension_payable_account"] as const).map((key,i)=><label key={key}>{["Net salaries payable","PAYE payable","NSSF payable","SHIF payable","Housing levy payable","Other deductions payable","NITA levy payable","Additional pension payable"][i]}<select required value={mapping[key]||""} onChange={e=>setMapping(v=>({...v,[key]:e.target.value}))}><option value="">Select liability account</option>{liabilities.map(a=><option key={a.id} value={a.id}>{a.code} — {a.name}</option>)}</select></label>)}
    <button className="primary" disabled={busy||!expenses.length||!liabilities.length}>{settings?"Update account mappings":"Save account mappings"}</button>
   </form>
  </div>}
  <div className="entry-panel">
   <h3>Calculate monthly payroll</h3>
   <form className="form-grid" onSubmit={createRun}>
    <label>Financial period<select required value={period} onChange={e=>setPeriod(e.target.value)}><option value="">Select period</option>{periods.map(p=><option key={p.id} value={p.id}>{p.name}{p.is_locked?" (locked)":""}</option>)}</select></label>
    <label>Payroll month<input type="date" required value={month} onChange={e=>setMonth(e.target.value)}/></label>
    <label>Pay date<input type="date" required value={payDate} onChange={e=>setPayDate(e.target.value)}/></label>
    <button className="primary" disabled={busy||!canWrite||!employees.some(e=>e.is_active)||!period}>{busy?"Calculating…":"Calculate draft payroll"}</button>
   </form>
  </div>
  <div className="entry-panel"><h3>Employees ({employees.length})</h3>
   <div className="table-wrap"><table><thead><tr><th>Number</th><th>Employee</th><th>Role</th><th>Basic salary</th><th>Cash allowances</th><th>Resident</th><th>Status</th></tr></thead><tbody>
    {employees.map(e=><tr key={e.id}><td>{e.employee_number}</td><td>{e.full_name}</td><td>{e.job_title||"—"}</td><td>{money(e.basic_salary,currency)}</td><td>{money(e.regular_cash_allowances,currency)}</td><td>{e.is_resident?"Yes":"No"}</td><td>{e.is_active?"Active":"Inactive"}</td></tr>)}
   </tbody></table></div>
  </div>
  <div className="entry-panel"><h3>Payroll runs</h3>
   {runs.map(r=><div key={r.id} className="payroll-run">
    <div className="panel-heading"><div><strong>{new Date(r.payroll_month+"T00:00:00").toLocaleDateString("en-KE",{month:"long",year:"numeric"})}</strong><p>{r.employee_count} employees · Gross {money(r.gross_total,currency)} · Net {money(r.net_total,currency)}</p></div><div><span className="status-pill">{r.status}</span> <a className="small-action" href={`${base}/runs/${r.id}/statutory-export/?schedule=REGISTER`}>Register CSV</a>{r.status==="POSTED"&&(["PAYE","NSSF","SHIF","AHL","PENSION","NITA"] as const).map(schedule=><a key={schedule} className="small-action" href={`${base}/runs/${r.id}/statutory-export/?schedule=${schedule}`}>{schedule} CSV</a>)}{r.status==="DRAFT"&&canWrite&&<button className="small-action" disabled={busy||!settings} onClick={()=>void postRun(r.id)}>Post payroll</button>}</div></div>
    <div className="table-wrap"><table><thead><tr><th>Employee</th><th>Gross</th><th>PAYE</th><th>NSSF</th><th>SHIF</th><th>Housing levy</th><th>NITA (employer)</th><th>Net pay</th></tr></thead><tbody>
     {(r.lines||[]).map((l:Row)=><tr key={l.id}><td>{l.employee_name}</td><td>{money(l.gross_pay,currency)}</td><td>{money(l.paye,currency)}</td><td>{money(l.nssf_employee,currency)}</td><td>{money(l.shif_employee,currency)}</td><td>{money(l.housing_levy_employee,currency)}</td><td>{money(l.nita_levy_employer,currency)}</td><td>{money(l.net_pay,currency)}</td></tr>)}
    </tbody></table></div>
   </div>)}
   {!runs.length&&<p className="muted">No payroll runs have been created.</p>}
  </div>
  <div className="entry-panel"><h3>Effective-dated statutory rules currently applied</h3><p className="muted">These values are configuration records, not a substitute for independent payroll review. Check the effective date for the payroll month and confirm each rate against the current official notice before posting.</p>
   <div className="table-wrap"><table><thead><tr><th>Rule</th><th>Effective from</th><th>To</th><th>Employee rate</th><th>Employer rate</th><th>Ceiling / fixed amount</th><th>PAYE deduction</th></tr></thead><tbody>
    {rules.map(r=><tr key={r.id}><td>{r.code}</td><td>{r.effective_from}</td><td>{r.effective_to||"Open"}</td><td>{(Number(r.employee_rate)*100).toFixed(3)}%</td><td>{(Number(r.employer_rate)*100).toFixed(3)}%</td><td>{r.ceiling?money(r.ceiling,currency):r.fixed_employer?money(r.fixed_employer,currency):r.fixed_employee?money(r.fixed_employee,currency):r.minimum_employee?money(r.minimum_employee,currency):"—"}</td><td>{r.deductible_for_paye?"Yes":"No"}</td></tr>)}
   </tbody></table></div>
   <div className="table-wrap"><table><thead><tr><th>PAYE lower bound</th><th>Upper bound</th><th>Rate</th><th>Effective from</th></tr></thead><tbody>{bands.map((b,i)=><tr key={b.id}><td>{money(b.lower_bound,currency)}</td><td>{b.upper_bound?money(b.upper_bound,currency):"No upper limit"}</td><td>{(Number(b.rate)*100).toFixed(2)}%</td><td>{b.effective_from}</td></tr>)}</tbody></table></div>
   {canAdmin&&<p className="muted">School administrators can maintain school-specific effective-dated overrides through the payroll rules API. Global statutory defaults are read-only.</p>}
  </div>
 </section>;
}
