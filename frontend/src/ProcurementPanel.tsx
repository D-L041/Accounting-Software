import { useEffect, useState } from "react";
import { api } from "./api";
import { money } from "./formatters";
type Row=Record<string,any>;
type Props={schoolId:number;currency:string;periods:Row[];accounts:Row[];canWrite:boolean;canApprove:boolean;onChanged?:()=>void};
const today=()=>new Date().toISOString().slice(0,10);
export default function ProcurementPanel({schoolId,currency,periods,accounts,canWrite,canApprove,onChanged}:Props){
 const base=`/api/schools/${schoolId}/expenses`;
 const [suppliers,setSuppliers]=useState<Row[]>([]),[categories,setCategories]=useState<Row[]>([]),[bills,setBills]=useState<Row[]>([]);
 const [supplierName,setSupplierName]=useState(""),[supplierPhone,setSupplierPhone]=useState("");
 const [bill,setBill]=useState({supplier:"",category:"",period:"",payable_account:"",supplier_invoice_number:"",bill_date:today(),due_date:today(),description:"",amount:""});
 const [payment,setPayment]=useState({bill:"",period:"",payment_date:today(),amount:"",payment_method:"BANK",payment_account:"",reference:""});
 const [error,setError]=useState(""),[busy,setBusy]=useState(false);
 const liabilities=accounts.filter(a=>a.category==="LIABILITY"&&a.is_active), assets=accounts.filter(a=>a.category==="ASSET"&&a.is_active);
 async function refresh(){const [s,c,b]=await Promise.all([api<Row[]>(`${base}/suppliers/`),api<Row[]>(`${base}/categories/`),api<Row[]>(`${base}/bills/`)]);setSuppliers(s);setCategories(c);setBills(b);}
 useEffect(()=>{void refresh().catch(e=>setError(e.message));},[schoolId]);
 async function createSupplier(e:React.FormEvent){e.preventDefault();setBusy(true);setError("");try{await api(`${base}/suppliers/`,{method:"POST",body:JSON.stringify({name:supplierName,phone:supplierPhone})});setSupplierName("");setSupplierPhone("");await refresh();onChanged?.();}catch(err){setError(err instanceof Error?err.message:"Could not save supplier.");}finally{setBusy(false);}}
 async function createBill(e:React.FormEvent){e.preventDefault();setBusy(true);setError("");try{await api(`${base}/bills/`,{method:"POST",body:JSON.stringify({...bill,supplier:Number(bill.supplier),category:Number(bill.category),period:Number(bill.period),payable_account:Number(bill.payable_account)})});setBill(v=>({...v,supplier_invoice_number:"",description:"",amount:""}));await refresh();onChanged?.();}catch(err){setError(err instanceof Error?err.message:"Could not create supplier bill.");}finally{setBusy(false);}}
 async function action(id:number,verb:string){setBusy(true);setError("");try{await api(`${base}/bills/${id}/${verb}/`,{method:"POST",body:JSON.stringify({})});await refresh();onChanged?.();}catch(err){setError(err instanceof Error?err.message:"Supplier bill action failed.");}finally{setBusy(false);}}
 async function payBill(e:React.FormEvent){e.preventDefault();setBusy(true);setError("");try{await api(`${base}/bills/${payment.bill}/payments/`,{method:"POST",body:JSON.stringify({...payment,bill:undefined,period:Number(payment.period),payment_account:Number(payment.payment_account)})});setPayment(v=>({...v,amount:"",reference:""}));await refresh();onChanged?.();}catch(err){setError(err instanceof Error?err.message:"Could not record supplier payment.");}finally{setBusy(false);}}
 return <section className="data-panel">
  <div className="panel-heading"><div><h2>Procurement & supplier payables</h2><p>Capture supplier invoices, submit them for approval, post approved bills and record part or full payments.</p></div><button className="secondary" onClick={()=>void refresh()}>Refresh</button></div>
  {error&&<div className="error-banner">{error}</div>}
  {canWrite&&<div className="setup-grid">
   <form className="entry-panel" onSubmit={createSupplier}><h3>Register supplier</h3><label>Supplier name<input required value={supplierName} onChange={e=>setSupplierName(e.target.value)}/></label><label>Phone<input value={supplierPhone} onChange={e=>setSupplierPhone(e.target.value)}/></label><button className="primary" disabled={busy}>Save supplier</button></form>
   <form className="entry-panel" onSubmit={createBill}><h3>Capture supplier invoice</h3>
    <label>Supplier<select required value={bill.supplier} onChange={e=>setBill(v=>({...v,supplier:e.target.value}))}><option value="">Select supplier</option>{suppliers.filter(s=>s.is_active).map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
    <label>Expense category<select required value={bill.category} onChange={e=>setBill(v=>({...v,category:e.target.value}))}><option value="">Select category</option>{categories.filter(c=>c.is_active).map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
    <label>Accounts payable<select required value={bill.payable_account} onChange={e=>setBill(v=>({...v,payable_account:e.target.value}))}><option value="">Select liability account</option>{liabilities.map(a=><option key={a.id} value={a.id}>{a.code} — {a.name}</option>)}</select></label>
    <label>Financial period<select required value={bill.period} onChange={e=>setBill(v=>({...v,period:e.target.value}))}><option value="">Select period</option>{periods.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
    <div className="form-grid"><label>Supplier invoice no.<input required value={bill.supplier_invoice_number} onChange={e=>setBill(v=>({...v,supplier_invoice_number:e.target.value}))}/></label><label>Amount<input required type="number" min="0.01" step="0.01" value={bill.amount} onChange={e=>setBill(v=>({...v,amount:e.target.value}))}/></label><label>Bill date<input required type="date" value={bill.bill_date} onChange={e=>setBill(v=>({...v,bill_date:e.target.value}))}/></label><label>Due date<input required type="date" value={bill.due_date} onChange={e=>setBill(v=>({...v,due_date:e.target.value}))}/></label></div>
    <label>Description<input required value={bill.description} onChange={e=>setBill(v=>({...v,description:e.target.value}))}/></label><button className="primary" disabled={busy}>Save draft bill</button>
   </form>
  </div>}
  {canWrite&&<form className="entry-panel" onSubmit={payBill}><h3>Pay supplier bill</h3><div className="form-grid">
   <label>Approved / posted bill<select required value={payment.bill} onChange={e=>setPayment(v=>({...v,bill:e.target.value}))}><option value="">Select bill</option>{bills.filter(b=>["POSTED","PART_PAID"].includes(b.status)&&Number(b.balance)>0).map(b=><option key={b.id} value={b.id}>{b.bill_number} · {b.supplier_name} · balance {money(b.balance,currency)}</option>)}</select></label>
   <label>Financial period<select required value={payment.period} onChange={e=>setPayment(v=>({...v,period:e.target.value}))}><option value="">Select period</option>{periods.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
   <label>Payment date<input type="date" required value={payment.payment_date} onChange={e=>setPayment(v=>({...v,payment_date:e.target.value}))}/></label>
   <label>Amount<input type="number" min="0.01" step="0.01" required value={payment.amount} onChange={e=>setPayment(v=>({...v,amount:e.target.value}))}/></label>
   <label>Method<select value={payment.payment_method} onChange={e=>setPayment(v=>({...v,payment_method:e.target.value}))}><option value="BANK">Bank</option><option value="MPESA">M-Pesa</option><option value="CASH">Cash</option></select></label>
   <label>Paid from<select required value={payment.payment_account} onChange={e=>setPayment(v=>({...v,payment_account:e.target.value}))}><option value="">Select asset account</option>{assets.map(a=><option key={a.id} value={a.id}>{a.code} — {a.name}</option>)}</select></label>
   <label>Reference<input value={payment.reference} onChange={e=>setPayment(v=>({...v,reference:e.target.value}))}/></label>
  </div><button className="primary" disabled={busy||!payment.bill}>Record payment</button></form>}
  <div className="entry-panel"><h3>Supplier bills & approval queue</h3><div className="table-wrap"><table><thead><tr><th>Bill</th><th>Supplier invoice</th><th>Supplier</th><th>Due</th><th>Amount</th><th>Balance</th><th>Status</th><th>Workflow</th></tr></thead><tbody>
   {bills.map(b=><tr key={b.id}><td>{b.bill_number}</td><td>{b.supplier_invoice_number}</td><td>{b.supplier_name}</td><td>{b.due_date}</td><td>{money(b.amount,currency)}</td><td>{money(b.balance,currency)}</td><td>{b.status}</td><td>{b.status==="DRAFT"&&canWrite?<button className="small-action" disabled={busy} onClick={()=>void action(b.id,"submit")}>Submit</button>:b.status==="SUBMITTED"&&canApprove?<button className="small-action" disabled={busy} onClick={()=>void action(b.id,"approve")}>Approve</button>:b.status==="APPROVED"&&canWrite?<button className="small-action" disabled={busy} onClick={()=>void action(b.id,"post")}>Post to ledger</button>:"—"}</td></tr>)}
  </tbody></table>{!bills.length&&<p className="muted">No supplier bills recorded.</p>}</div></div>
 </section>;
}
