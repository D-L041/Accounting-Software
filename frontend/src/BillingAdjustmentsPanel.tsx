import { useEffect, useState } from "react";
import { api } from "./api";
import { money } from "./formatters";

type Row = Record<string, any>;
type Props = { schoolId:number; currency:string; periods:Row[]; accounts:Row[]; canWrite:boolean; onChanged?:()=>void };
const today=()=>new Date().toISOString().slice(0,10);

export default function BillingAdjustmentsPanel({schoolId,currency,periods,accounts,canWrite,onChanged}:Props){
  const base=`/api/schools/${schoolId}/billing`;
  const [invoices,setInvoices]=useState<Row[]>([]);
  const [payments,setPayments]=useState<Row[]>([]);
  const [notes,setNotes]=useState<Row[]>([]);
  const [invoiceId,setInvoiceId]=useState("");
  const [creditLineId,setCreditLineId]=useState("");
  const [periodId,setPeriodId]=useState("");
  const [creditDate,setCreditDate]=useState(today());
  const [reason,setReason]=useState("");
  const [creditAmount,setCreditAmount]=useState("");
  const [paymentId,setPaymentId]=useState("");
  const [refundInvoice,setRefundInvoice]=useState("");
  const [refundAccount,setRefundAccount]=useState("");
  const [refundPeriod,setRefundPeriod]=useState("");
  const [refundDate,setRefundDate]=useState(today());
  const [refundAmount,setRefundAmount]=useState("");
  const [refundReference,setRefundReference]=useState("");
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  const selectedInvoice=invoices.find(i=>String(i.id)===invoiceId);
  const selectedPayment=payments.find(p=>String(p.id)===paymentId);
  const assetAccounts=accounts.filter(a=>a.category==="ASSET"&&a.is_active);
  async function refresh(){
    const [i,p,n]=await Promise.all([api<Row[]>(`${base}/invoices/`),api<Row[]>(`${base}/payments/`),api<Row[]>(`${base}/credit-notes/`)]);
    setInvoices(i);setPayments(p);setNotes(n);
  }
  useEffect(()=>{void refresh().catch(e=>setError(e.message));},[schoolId]);
  async function createCredit(e:React.FormEvent){
    e.preventDefault();setBusy(true);setError("");
    try{
      await api(`${base}/credit-notes/`,{method:"POST",body:JSON.stringify({
        invoice:Number(invoiceId),period:Number(periodId),credit_date:creditDate,reason,
        lines:[{invoice_line:Number(creditLineId),amount:creditAmount}],
      })});
      setReason("");setCreditAmount("");await refresh();onChanged?.();
    }catch(err){setError(err instanceof Error?err.message:"Could not create credit note.");}
    finally{setBusy(false);}
  }
  async function postCredit(id:number){
    setBusy(true);setError("");
    try{await api(`${base}/credit-notes/${id}/post/`,{method:"POST",body:JSON.stringify({})});await refresh();onChanged?.();}
    catch(err){setError(err instanceof Error?err.message:"Could not post credit note.");}
    finally{setBusy(false);}
  }
  async function refund(e:React.FormEvent){
    e.preventDefault();setBusy(true);setError("");
    try{
      await api(`${base}/payments/${paymentId}/refunds/`,{method:"POST",body:JSON.stringify({
        invoice:Number(refundInvoice),period:Number(refundPeriod),payment_account:Number(refundAccount),
        refund_date:refundDate,amount:refundAmount,reference:refundReference,
      })});
      setRefundAmount("");setRefundReference("");await refresh();onChanged?.();
    }catch(err){setError(err instanceof Error?err.message:"Could not record refund.");}
    finally{setBusy(false);}
  }
  return <section className="data-panel">
    <div className="panel-heading"><div><h2>Credit notes & payment refunds</h2><p>Post invoice adjustments and reverse money actually returned to a parent or payer.</p></div><button className="secondary" onClick={()=>void refresh()}>Refresh</button></div>
    {error&&<div className="error-banner">{error}</div>}
    {canWrite&&<div className="setup-grid">
      <form className="entry-panel" onSubmit={createCredit}>
        <h3>Create credit note</h3>
        <label>Issued invoice<select required value={invoiceId} onChange={e=>{setInvoiceId(e.target.value);setCreditAmount("");setCreditLineId(String(invoices.find(i=>String(i.id)===e.target.value)?.line_items?.[0]?.id||""));}}><option value="">Select invoice</option>{invoices.filter(i=>!["DRAFT","VOID"].includes(i.status)).map(i=><option key={i.id} value={i.id}>{i.invoice_number} · {i.student_name} · balance {money(i.balance,currency)}</option>)}</select></label>
        <label>Financial period<select required value={periodId} onChange={e=>setPeriodId(e.target.value)}><option value="">Select period</option>{periods.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        <label>Credit date<input type="date" required value={creditDate} onChange={e=>setCreditDate(e.target.value)}/></label>
        <label>Reason<input required value={reason} onChange={e=>setReason(e.target.value)} placeholder="e.g. Fee overcharge adjustment"/></label>
        <label>Invoice line<select required value={creditLineId} disabled={!selectedInvoice} onChange={e=>setCreditLineId(e.target.value)}><option value="">Select invoice line</option>{(selectedInvoice?.line_items||[]).map((l:Row)=><option key={l.id} value={l.id}>{l.description||l.fee_item_name} · original {money(l.amount,currency)}</option>)}</select></label>
        <label>Credit amount<input type="number" step="0.01" min="0.01" max={selectedInvoice?.line_items?.find((l:Row)=>String(l.id)===creditLineId)?.amount||undefined} required value={creditAmount} onChange={e=>setCreditAmount(e.target.value)}/></label>
        <button className="primary" disabled={busy||!selectedInvoice?.line_items?.length||!creditLineId}>{busy?"Saving…":"Save draft credit note"}</button>
      </form>
      <form className="entry-panel" onSubmit={refund}>
        <h3>Record payment refund</h3>
        <label>Original receipt<select required value={paymentId} onChange={e=>{setPaymentId(e.target.value);setRefundInvoice("");}}><option value="">Select receipt</option>{payments.map(p=><option key={p.id} value={p.id}>{p.receipt_number} · {p.student_name} · {money(p.amount,currency)}</option>)}</select></label>
        <label>Invoice to reverse<select required value={refundInvoice} onChange={e=>setRefundInvoice(e.target.value)}><option value="">Select invoice</option>{invoices.filter(i=>!["DRAFT","VOID"].includes(i.status) && (!selectedPayment||i.student===selectedPayment.student)).map(i=><option key={i.id} value={i.id}>{i.invoice_number} · {i.student_name}</option>)}</select></label>
        <label>Refund from account<select required value={refundAccount} onChange={e=>setRefundAccount(e.target.value)}><option value="">Select cash / bank / M-Pesa account</option>{assetAccounts.map(a=><option key={a.id} value={a.id}>{a.code} — {a.name}</option>)}</select></label>
        <label>Financial period<select required value={refundPeriod} onChange={e=>setRefundPeriod(e.target.value)}><option value="">Select period</option>{periods.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        <label>Refund date<input type="date" required value={refundDate} onChange={e=>setRefundDate(e.target.value)}/></label>
        <label>Refund amount<input type="number" step="0.01" min="0.01" required value={refundAmount} onChange={e=>setRefundAmount(e.target.value)}/></label>
        <label>Refund reference<input value={refundReference} onChange={e=>setRefundReference(e.target.value)} /></label>
        <button className="primary" disabled={busy||!selectedPayment}>{busy?"Saving…":"Record refund"}</button>
      </form>
    </div>}
    <div className="entry-panel"><h3>Credit note register</h3>
      <div className="table-wrap"><table><thead><tr><th>Credit note</th><th>Invoice</th><th>Date</th><th>Reason</th><th>Amount</th><th>Status</th><th>Action</th></tr></thead><tbody>
        {notes.map(n=><tr key={n.id}><td>{n.credit_note_number}</td><td>{n.invoice_number}</td><td>{n.credit_date}</td><td>{n.reason}</td><td>{money(n.amount,currency)}</td><td>{n.status}</td><td>{n.status==="DRAFT"&&canWrite?<button className="small-action" disabled={busy} onClick={()=>void postCredit(n.id)}>Post</button>:"—"}</td></tr>)}
      </tbody></table>{!notes.length&&<p className="muted">No credit notes recorded yet.</p>}</div>
    </div>
  </section>;
}
