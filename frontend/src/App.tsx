import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  LayoutDashboard, GraduationCap, ReceiptText, Wallet, BookOpen, Landmark,
  Users, Settings, Menu, Bell, Search, ArrowUpRight, ArrowDownRight,
  ShieldCheck, LogOut, Plus, RefreshCw, AlertCircle, CheckCircle2, ClipboardList,
} from "lucide-react";
import { api, login, logout, School, User } from "./api";
import ReportPanel from "./ReportPanel";

type Row = Record<string, any>;
const nav = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Students & Classes", icon: GraduationCap },
  { label: "Fees & Invoices", icon: ReceiptText },
  { label: "Payments & Receipts", icon: Wallet },
  { label: "Expenses & Suppliers", icon: ArrowDownRight },
  { label: "General Ledger", icon: BookOpen },
  { label: "Cashbook & Banks", icon: Landmark, disabled: true },
  { label: "Staff & Payroll", icon: Users, disabled: true },
  { label: "Reports", icon: ArrowUpRight },
  { label: "Audit Log", icon: ClipboardList },
  { label: "Settings", icon: Settings },
];
const today = new Date().toISOString().slice(0, 10);
const money = (value: unknown, currency = "KES") => new Intl.NumberFormat("en-KE", { style: "currency", currency, maximumFractionDigits: 2 }).format(Number(value || 0));
const errorText = (error: unknown) => error instanceof Error ? error.message : "Something went wrong. Please try again.";

function LoginScreen({ onLogin }: { onLogin: (username: string, password: string) => Promise<void> }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { await onLogin(username, password); } catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  }
  return <div className="auth-screen"><form className="auth-card" onSubmit={submit}>
    <div className="brand auth-brand"><div className="crest"><GraduationCap size={25}/></div><div><strong>PRECIOUS</strong><small>SCHOOLBOOKS</small></div></div>
    <div className="eyebrow">SECURE SCHOOL FINANCE</div><h1>Welcome back</h1><p>Sign in to your school accounting workspace.</p>
    {error && <div className="error-banner"><AlertCircle size={16}/>{error}</div>}
    <label>Username<input autoComplete="username" value={username} onChange={e=>setUsername(e.target.value)} required /></label>
    <label>Password<input type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required /></label>
    <button className="primary full" disabled={busy}>{busy ? "Signing in…" : "Sign in securely"}</button>
    <small className="muted">Access is managed by your school administrator.</small>
  </form></div>;
}

function DataTable({ rows, columns, currency, empty }: { rows: Row[]; columns: {key:string;label:string;format?:(v:any,row:Row)=>string}[]; currency: string; empty: string }) {
  if (!rows.length) return <div className="table-empty">{empty}</div>;
  return <div className="table-wrap"><table><thead><tr>{columns.map(c=><th key={c.key}>{c.label}</th>)}</tr></thead><tbody>
    {rows.map((row,i)=><tr key={row.id ?? i}>{columns.map(c=><td key={c.key}>{c.format ? c.format(row[c.key],row) : String(row[c.key] ?? "—")}</td>)}</tr>)}
  </tbody></table></div>;
}

export default function App() {
  const [user,setUser] = useState<User|null>(null);
  const [school,setSchool] = useState<School|null>(null);
  const [active,setActive] = useState("Overview");
  const [menu,setMenu] = useState(false);
  const [loading,setLoading] = useState(true);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [success,setSuccess] = useState("");
  const [rows,setRows] = useState<Row[]>([]);
  const [students,setStudents] = useState<Row[]>([]);
  const [years,setYears] = useState<Row[]>([]);
  const [periods,setPeriods] = useState<Row[]>([]);
  const [feeItems,setFeeItems] = useState<Row[]>([]);
  const [accounts,setAccounts] = useState<Row[]>([]);
  const [categories,setCategories] = useState<Row[]>([]);
  const [suppliers,setSuppliers] = useState<Row[]>([]);
  const [billingSettings,setBillingSettings] = useState<Row|null>(null);
  const [trialBalance,setTrialBalance] = useState<Row|null>(null);
  const [auditRows,setAuditRows] = useState<Row[]>([]);
  const [reportPeriod,setReportPeriod] = useState("");
  const [reportType,setReportType] = useState("trial-balance");
  const [invoices,setInvoices] = useState<Row[]>([]);
  const [form,setForm] = useState<Record<string,string>>({});
  const [newSchool,setNewSchool] = useState({name:"",code:"",address:"",phone:"",email:""});

  const schoolBase = school ? `/api/schools/${school.id}` : "";
  const setField = (key:string,value:string) => setForm(old=>({...old,[key]:value}));
  const clearMessages = () => { setError(""); setSuccess(""); };

  const refreshSession = useCallback(async () => {
    try {
      const response = await api<{user:User}>("/api/auth/me/");
      setUser(response.user);
      setSchool(current => current && response.user.schools.some(s=>s.id===current.id) ? current : response.user.schools[0] || null);
    } catch { setUser(null); setSchool(null); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void refreshSession(); }, [refreshSession]);

  const loadData = useCallback(async () => {
    if (!school) return;
    setLoading(true); setError("");
    try {
      const [studentRows, yearRows, periodRows, accountRows, feeRows, invoiceRows, paymentRows, expenseRows, categoryRows, supplierRows, billingRows] = await Promise.all([
        api<Row[]>(`${schoolBase}/students/`),
        api<Row[]>(`${schoolBase}/academic-years/`),
        api<Row[]>(`${schoolBase}/ledger/periods/`),
        api<Row[]>(`${schoolBase}/ledger/accounts/`),
        api<Row[]>(`${schoolBase}/billing/fee-items/`),
        api<Row[]>(`${schoolBase}/billing/invoices/`),
        api<Row[]>(`${schoolBase}/billing/payments/`),
        api<Row[]>(`${schoolBase}/expenses/`),
        api<Row[]>(`${schoolBase}/expenses/categories/`),
        api<Row[]>(`${schoolBase}/expenses/suppliers/`),
        api<Row[]>(`${schoolBase}/billing/settings/`),
      ]);
      setStudents(studentRows); setYears(yearRows); setPeriods(periodRows); setAccounts(accountRows);
      setFeeItems(feeRows); setInvoices(invoiceRows); setCategories(categoryRows); setSuppliers(supplierRows); setBillingSettings(billingRows[0] || null);
      if (active==="Overview") { const activity: Row[] = [...invoiceRows.slice(0,5).map(x=>({...x,record_type:"Invoice"})), ...paymentRows.slice(0,5).map(x=>({...x,record_type:"Receipt"})), ...expenseRows.slice(0,5).map(x=>({...x,record_type:"Expense"}))]; setRows(activity.sort((a,b)=>String(b.created_at||b.invoice_date||b.payment_date||b.expense_date).localeCompare(String(a.created_at||a.invoice_date||a.payment_date||a.expense_date))).slice(0,8)); }
      else if (active==="Students & Classes") setRows(studentRows);
      else if (active==="Fees & Invoices") setRows(invoiceRows);
      else if (active==="Payments & Receipts") setRows(paymentRows);
      else if (active==="Expenses & Suppliers") setRows(expenseRows);
      else if (active==="General Ledger") setRows(accountRows);
      else if (active==="Settings") setRows(periodRows);
    } catch(e) { setError(errorText(e)); }
    finally { setLoading(false); }
  }, [school,schoolBase,active]);

  useEffect(() => { if(user && school) void loadData(); }, [user,school,active,loadData]);
  useEffect(() => {
    if(active!=="Audit Log" || !school) return;
    api<Row[]>(`/api/schools/${school.id}/audit/`).then(setAuditRows).catch(e=>setError(errorText(e)));
  },[active,school]);
  useEffect(() => {
    if(active!=="Reports" || !school) return;
    const periodId = reportPeriod || String(periods[0]?.id || "");
    if(!periodId) { setTrialBalance(null); return; }
    if(!reportPeriod) setReportPeriod(periodId);
    const route = reportType==="income-expenditure" ? "income-expenditure" : reportType==="balance-sheet" ? "balance-sheet" : "trial-balance";
    api<Row>("/api/schools/" + school.id + "/ledger/reports/" + route + "/?period=" + periodId)
      .then(setTrialBalance).catch(e=>setError(errorText(e)));
  },[active,school,periods,reportPeriod,reportType]);

  async function handleLogin(username:string,password:string) {
    const response=await login(username,password);
    setUser(response.user); setSchool(response.user.schools[0] || null);
  }
  async function handleLogout() {
    try { await logout(); } finally { setUser(null); setSchool(null); setRows([]); }
  }
  async function submitAction(path:string, payload:Row, message:string) {
    setBusy(true); clearMessages();
    try { await api(path,{method:"POST",body:JSON.stringify(payload)}); setSuccess(message); setForm({}); await loadData(); }
    catch(e) { setError(errorText(e)); }
    finally { setBusy(false); }
  }
  async function createSchool(event:FormEvent) {
    event.preventDefault(); setBusy(true); clearMessages();
    try {
      await api("/api/schools/",{method:"POST",body:JSON.stringify(newSchool)});
      await refreshSession(); setSuccess("School workspace created.");
    } catch(e) { setError(errorText(e)); } finally { setBusy(false); }
  }
  async function createClassroom(event:FormEvent) {
    event.preventDefault();
    await submitAction(schoolBase + "/classrooms/",{academic_year:Number(form.class_year),name:form.class_name,stream:form.class_stream||"",class_teacher:form.class_teacher||""},"Class or stream created.");
  }
  async function createStudent(event:FormEvent) {
    event.preventDefault();
    await submitAction(`${schoolBase}/students/`,{admission_number:form.admission_number,first_name:form.first_name,last_name:form.last_name,middle_name:form.middle_name||"",guardian_name:form.guardian_name||"",guardian_phone:form.guardian_phone||"",admission_date:form.admission_date||today,classroom:form.classroom?Number(form.classroom):null},"Student record created.");
  }
  async function createInvoice(event:FormEvent) {
    event.preventDefault();
    await submitAction(`${schoolBase}/billing/invoices/`,{student:Number(form.student),academic_year:Number(form.academic_year),period:Number(form.period),invoice_date:form.invoice_date||today,due_date:form.due_date||today,notes:form.notes||"",lines:[{fee_item:Number(form.fee_item),quantity:"1.00",unit_amount:form.unit_amount,description:form.description||""}]},"Draft invoice created.");
  }

  async function createAccount(event:FormEvent) {
    event.preventDefault();
    await submitAction(`${schoolBase}/ledger/accounts/`,{code:form.account_code,name:form.account_name,category:form.account_category},"Ledger account created.");
  }
  async function createAcademicYear(event:FormEvent) {
    event.preventDefault();
    await submitAction(schoolBase + "/academic-years/",{name:form.year_name,starts_on:form.year_start,ends_on:form.year_end,is_current:form.year_current==="true"},"Academic year created.");
  }
  async function createPeriod(event:FormEvent) {
    event.preventDefault();
    await submitAction(`${schoolBase}/ledger/periods/`,{name:form.period_name,starts_on:form.period_start,ends_on:form.period_end},"Financial period created.");
  }
  async function createFeeItem(event:FormEvent) {
    event.preventDefault();
    await submitAction(`${schoolBase}/billing/fee-items/`,{code:form.fee_code,name:form.fee_name,description:form.fee_description||"",income_account:Number(form.income_account)},"Fee item created.");
  }
  async function createExpenseCategory(event:FormEvent) {
    event.preventDefault();
    await submitAction(`${schoolBase}/expenses/categories/`,{code:form.expense_code,name:form.expense_name,expense_account:Number(form.expense_account)},"Expense category created.");
  }
  async function saveBillingSettings(event:FormEvent) {
    event.preventDefault(); setBusy(true); clearMessages();
    const payload={receivables_account:Number(form.receivables_account),cash_account:Number(form.cash_account),bank_account:Number(form.bank_account),mpesa_account:Number(form.mpesa_account),invoice_prefix:form.invoice_prefix||"INV",receipt_prefix:form.receipt_prefix||"RCT"};
    try {
      if(billingSettings?.id) await api(`${schoolBase}/billing/settings/${billingSettings.id}/`,{method:"PATCH",body:JSON.stringify(payload)});
      else await api(`${schoolBase}/billing/settings/`,{method:"POST",body:JSON.stringify(payload)});
      setSuccess("Billing ledger mappings saved."); await loadData();
    } catch(e) { setError(errorText(e)); } finally { setBusy(false); }
  }
  async function issueInvoice(id:number) {
    setBusy(true); clearMessages();
    try { await api(`${schoolBase}/billing/invoices/${id}/issue/`,{method:"POST",body:JSON.stringify({})}); setSuccess("Invoice issued and posted to the ledger."); await loadData(); }
    catch(e) { setError(errorText(e)); } finally { setBusy(false); }
  }
  async function createPayment(event:FormEvent) {
    event.preventDefault();
    await submitAction(`${schoolBase}/billing/payments/`,{student:Number(form.student),payment_date:form.payment_date||today,method:form.method||"MPESA",amount:form.amount,transaction_reference:form.transaction_reference||"",notes:form.payment_notes||"",allocations:[{invoice_id:Number(form.invoice_id),amount:form.amount}]},"Payment received and receipt recorded.");
  }
  async function createSupplier(event:FormEvent) {
    event.preventDefault();
    await submitAction(schoolBase + "/expenses/suppliers/",{name:form.supplier_name,contact_person:form.contact_person||"",phone:form.supplier_phone||"",email:form.supplier_email||"",tax_pin:form.tax_pin||"",address:form.supplier_address||""},"Supplier saved.");
  }
  async function createExpense(event:FormEvent) {
    event.preventDefault();
    await submitAction(`${schoolBase}/expenses/`,{supplier:form.supplier?Number(form.supplier):null,category:Number(form.category),period:Number(form.period),expense_date:form.expense_date||today,description:form.description,amount:form.amount,payment_method:form.payment_method||"MPESA",reference:form.reference||""},"Draft expense recorded.");
  }
  async function postExpense(id:number) {
    setBusy(true); clearMessages();
    try { await api(`${schoolBase}/expenses/${id}/post/`,{method:"POST",body:JSON.stringify({})}); setSuccess("Expense posted to the ledger."); await loadData(); }
    catch(e) { setError(errorText(e)); } finally { setBusy(false); }
  }

  const totals = useMemo(()=>({
    outstanding: invoices.filter(x=>x.status!=="PAID"&&x.status!=="DRAFT"&&x.status!=="VOID").reduce((n,x)=>n+Number(x.balance||0),0),
    invoiced: invoices.reduce((n,x)=>n+Number(x.total_amount||0),0),
    students: students.filter(x=>x.status==="ACTIVE").length,
    invoices: invoices.filter(x=>x.status!=="DRAFT"&&x.status!=="VOID").length,
  }),[invoices,students]);

  if(loading && !user) return <div className="loading-screen"><div className="crest"><GraduationCap/></div><span>Loading Precious SchoolBooks…</span></div>;
  if(!user) return <LoginScreen onLogin={handleLogin}/>;
  if(!school) return <div className="auth-screen"><form className="auth-card" onSubmit={createSchool}><div className="brand auth-brand"><div className="crest"><GraduationCap/></div><div><strong>PRECIOUS</strong><small>SCHOOLBOOKS</small></div></div><h1>Create your school workspace</h1><p>Your account has no school workspace yet. Create one to get started.</p>{error&&<div className="error-banner">{error}</div>}<label>School name<input required value={newSchool.name} onChange={e=>setNewSchool({...newSchool,name:e.target.value})}/></label><label>School code<input required value={newSchool.code} onChange={e=>setNewSchool({...newSchool,code:e.target.value})} placeholder="st-stephen-school"/></label><label>Phone<input value={newSchool.phone} onChange={e=>setNewSchool({...newSchool,phone:e.target.value})}/></label><button className="primary full" disabled={busy}>Create workspace</button><button type="button" className="text-button" onClick={handleLogout}>Sign out</button></form></div>;

  const columns = active==="Students & Classes"
    ? [{key:"admission_number",label:"Admission No."},{key:"full_name",label:"Student"},{key:"classroom_name",label:"Class"},{key:"guardian_name",label:"Parent / Guardian"},{key:"guardian_phone",label:"Phone"},{key:"status",label:"Status"}]
    : active==="Fees & Invoices"
    ? [{key:"invoice_number",label:"Invoice"},{key:"student_name",label:"Student"},{key:"invoice_date",label:"Date"},{key:"due_date",label:"Due date"},{key:"total_amount",label:"Total",format:(v:any)=>money(v,school.currency)},{key:"amount_paid",label:"Paid",format:(v:any)=>money(v,school.currency)},{key:"balance",label:"Balance",format:(v:any)=>money(v,school.currency)},{key:"status",label:"Status"}]
    : active==="Payments & Receipts"
    ? [{key:"receipt_number",label:"Receipt"},{key:"student_name",label:"Student"},{key:"payment_date",label:"Date"},{key:"method",label:"Method"},{key:"transaction_reference",label:"Reference"},{key:"amount",label:"Amount",format:(v:any)=>money(v,school.currency)}]
    : active==="Expenses & Suppliers"
    ? [{key:"expense_number",label:"Expense No."},{key:"expense_date",label:"Date"},{key:"description",label:"Description"},{key:"category_name",label:"Category"},{key:"supplier_name",label:"Supplier"},{key:"payment_method",label:"Method"},{key:"amount",label:"Amount",format:(v:any)=>money(v,school.currency)},{key:"status",label:"Status"}]
    : active==="General Ledger"
    ? [{key:"code",label:"Code"},{key:"name",label:"Account"},{key:"category",label:"Category"},{key:"is_active",label:"Active",format:(v:any)=>v?"Yes":"No"}]
    : active==="Settings"
    ? [{key:"name",label:"Financial period"},{key:"starts_on",label:"Start"},{key:"ends_on",label:"End"},{key:"is_locked",label:"Locked",format:(v:any)=>v?"Yes":"No"}]
    : active==="Audit Log"
    ? [{key:"created_at",label:"Date / time"},{key:"actor_name",label:"User"},{key:"action",label:"Action"},{key:"entity_type",label:"Record type"},{key:"entity_id",label:"Record ID"},{key:"summary",label:"Description"}]
    : [{key:"record_type",label:"Type"},{key:"invoice_number",label:"Reference",format:(v:any,row:Row)=>v||row.receipt_number||row.expense_number||"—"},{key:"student_name",label:"Student"},{key:"description",label:"Description"},{key:"amount",label:"Amount",format:(v:any,row:Row)=>money(v||row.total_amount||0,school.currency)},{key:"status",label:"Status"}];

  const heading = active==="Overview" ? "Financial overview" : active;
  const canWrite = ["OWNER","ADMIN","ACCOUNTANT","BURSAR"].includes(school.role);
  return <div className="shell">
    <aside className={menu?"sidebar open":"sidebar"}>
      <div className="brand"><div className="crest"><GraduationCap size={24}/></div><div><strong>PRECIOUS</strong><small>SCHOOLBOOKS</small></div></div>
      <div className="school-tag">{school.name.toUpperCase()} WORKSPACE</div>
      <nav>{nav.filter(item=>item.label!=="Audit Log"||["OWNER","ADMIN","ACCOUNTANT"].includes(school.role)).map(({label,icon:Icon,disabled})=><button key={label} disabled={disabled} title={disabled?"Coming in a later release":label} className={active===label?"nav-item selected":"nav-item"} onClick={()=>{setActive(label);setMenu(false);clearMessages();}}><Icon size={18}/><span>{label}</span>{disabled&&<small className="soon">Soon</small>}</button>)}</nav>
      <div className="side-foot"><ShieldCheck size={17}/><span>{school.role.toLowerCase()} access</span></div>
    </aside>
    <main className="main">
      <header><button className="icon-btn mobile" onClick={()=>setMenu(!menu)}><Menu/></button><div className="crumb">Precious SchoolBooks <span>/</span> {active}</div><div className="head-actions"><button className="icon-btn" title="Refresh" onClick={()=>void loadData()}><RefreshCw/></button><div className="avatar">{user.name.slice(0,2).toUpperCase()}</div><div className="user-label">{user.name}<small>{school.role}</small></div><button className="icon-btn" title="Sign out" onClick={handleLogout}><LogOut/></button></div></header>
      <section className="content">
        <div className="welcome"><div><div className="eyebrow">SCHOOL FINANCE WORKSPACE</div><h1>{heading}</h1><p>{school.name} · Kenyan Shillings (KES)</p></div><div className="period">Signed in as <strong>{user.username}</strong></div></div>
        {error&&<div className="error-banner"><AlertCircle size={16}/>{error}</div>}
        {success&&<div className="success-banner"><CheckCircle2 size={16}/>{success}</div>}
        {active==="Overview"&&<div className="metric-grid">
          <div className="metric"><span>Active students</span><strong>{totals.students}</strong><small>Enrolled student records</small></div>
          <div className="metric"><span>Invoices issued</span><strong>{totals.invoices}</strong><small>{money(totals.invoiced,school.currency)} total invoiced</small></div>
          <div className="metric"><span>Outstanding fees</span><strong>{money(totals.outstanding,school.currency)}</strong><small>Excludes drafts and void invoices</small></div>
          <div className="metric"><span>Fee items</span><strong>{feeItems.length}</strong><small>Configured income categories</small></div>
        </div>}

        {canWrite&&active==="Students & Classes"&&<form className="entry-panel" onSubmit={createClassroom}><div className="panel-heading"><div><h2>Create class or stream</h2><p>Assign classes to an academic year.</p></div><Plus size={18}/></div><div className="form-grid"><label>Academic year<select required value={form.class_year||""} onChange={e=>setField("class_year",e.target.value)}><option value="">Select year</option>{years.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label><label>Class name<input required value={form.class_name||""} onChange={e=>setField("class_name",e.target.value)} placeholder="Grade 1 / Form 1"/></label><label>Stream<input value={form.class_stream||""} onChange={e=>setField("class_stream",e.target.value)} placeholder="East / A"/></label><label>Class teacher<input value={form.class_teacher||""} onChange={e=>setField("class_teacher",e.target.value)}/></label></div><button className="primary" disabled={busy||!years.length}>Save class</button></form>}
        {canWrite&&active==="Students & Classes"&&<form className="entry-panel" onSubmit={createStudent}><div className="panel-heading"><div><h2>Register student</h2><p>Add a student to this school workspace.</p></div><Plus size={18}/></div><div className="form-grid"><label>Admission number<input required value={form.admission_number||""} onChange={e=>setField("admission_number",e.target.value)}/></label><label>First name<input required value={form.first_name||""} onChange={e=>setField("first_name",e.target.value)}/></label><label>Middle name<input value={form.middle_name||""} onChange={e=>setField("middle_name",e.target.value)}/></label><label>Last name<input required value={form.last_name||""} onChange={e=>setField("last_name",e.target.value)}/></label><label>Parent / guardian<input value={form.guardian_name||""} onChange={e=>setField("guardian_name",e.target.value)}/></label><label>Guardian phone<input value={form.guardian_phone||""} onChange={e=>setField("guardian_phone",e.target.value)}/></label><label>Admission date<input type="date" value={form.admission_date||today} onChange={e=>setField("admission_date",e.target.value)}/></label></div><button className="primary" disabled={busy}>Save student</button></form>}
        {canWrite&&active==="Fees & Invoices"&&<form className="entry-panel" onSubmit={createInvoice}><div className="panel-heading"><div><h2>Create fee invoice</h2><p>Create a draft, review it, then issue it to the ledger.</p></div><Plus size={18}/></div><div className="form-grid"><label>Student<select required value={form.student||""} onChange={e=>setField("student",e.target.value)}><option value="">Select student</option>{students.map(x=><option value={x.id} key={x.id}>{x.admission_number} — {x.full_name}</option>)}</select></label><label>Academic year<select required value={form.academic_year||""} onChange={e=>setField("academic_year",e.target.value)}><option value="">Select year</option>{years.map(x=><option value={x.id} key={x.id}>{x.name}</option>)}</select></label><label>Financial period<select required value={form.period||""} onChange={e=>setField("period",e.target.value)}><option value="">Select period</option>{periods.filter(x=>!x.is_locked).map(x=><option value={x.id} key={x.id}>{x.name}</option>)}</select></label><label>Fee item<select required value={form.fee_item||""} onChange={e=>setField("fee_item",e.target.value)}><option value="">Select fee item</option>{feeItems.filter(x=>x.is_active).map(x=><option value={x.id} key={x.id}>{x.name}</option>)}</select></label><label>Amount (KES)<input type="number" min="0" step="0.01" required value={form.unit_amount||""} onChange={e=>setField("unit_amount",e.target.value)}/></label><label>Invoice date<input type="date" value={form.invoice_date||today} onChange={e=>setField("invoice_date",e.target.value)}/></label><label>Due date<input type="date" value={form.due_date||today} onChange={e=>setField("due_date",e.target.value)}/></label><label>Description<input value={form.description||""} onChange={e=>setField("description",e.target.value)}/></label></div><button className="primary" disabled={busy||!students.length||!years.length||!periods.length||!feeItems.length}>Create draft invoice</button>{(!years.length||!periods.length||!feeItems.length)&&<small className="muted">Setup required: add an academic year, financial period, chart of accounts, billing settings and fee items before invoicing.</small>}</form>}
        {canWrite&&active==="Payments & Receipts"&&<form className="entry-panel" onSubmit={createPayment}><div className="panel-heading"><div><h2>Record fee payment</h2><p>Allocate a receipt to an issued student invoice.</p></div><Plus size={18}/></div><div className="form-grid"><label>Student<select required value={form.student||""} onChange={e=>{setField("student",e.target.value);setField("invoice_id","");}}><option value="">Select student</option>{students.map(x=><option value={x.id} key={x.id}>{x.admission_number} — {x.full_name}</option>)}</select></label><label>Invoice<select required value={form.invoice_id||""} onChange={e=>setField("invoice_id",e.target.value)}><option value="">Select invoice</option>{invoices.filter(x=>String(x.student)===form.student&&["ISSUED","PART_PAID"].includes(x.status)).map(x=><option value={x.id} key={x.id}>{x.invoice_number} · Balance {money(x.balance,school.currency)}</option>)}</select></label><label>Amount received<input required type="number" min="0.01" step="0.01" value={form.amount||""} onChange={e=>setField("amount",e.target.value)}/></label><label>Payment method<select value={form.method||"MPESA"} onChange={e=>setField("method",e.target.value)}><option value="MPESA">M-Pesa</option><option value="CASH">Cash</option><option value="BANK">Bank</option></select></label><label>Payment date<input type="date" value={form.payment_date||today} onChange={e=>setField("payment_date",e.target.value)}/></label><label>M-Pesa / bank reference<input value={form.transaction_reference||""} onChange={e=>setField("transaction_reference",e.target.value)}/></label></div><button className="primary" disabled={busy||!form.invoice_id}>Record payment and issue receipt</button></form>}

        {canWrite&&active==="Expenses & Suppliers"&&<form className="entry-panel" onSubmit={createSupplier}><div className="panel-heading"><div><h2>Add supplier</h2><p>Maintain school supplier and vendor details.</p></div><Plus size={18}/></div><div className="form-grid"><label>Supplier name<input required value={form.supplier_name||""} onChange={e=>setField("supplier_name",e.target.value)}/></label><label>Contact person<input value={form.contact_person||""} onChange={e=>setField("contact_person",e.target.value)}/></label><label>Phone<input value={form.supplier_phone||""} onChange={e=>setField("supplier_phone",e.target.value)}/></label><label>Email<input type="email" value={form.supplier_email||""} onChange={e=>setField("supplier_email",e.target.value)}/></label><label>KRA PIN<input value={form.tax_pin||""} onChange={e=>setField("tax_pin",e.target.value)}/></label><label>Address<input value={form.supplier_address||""} onChange={e=>setField("supplier_address",e.target.value)}/></label></div><button className="primary" disabled={busy}>Save supplier</button></form>}
        {canWrite&&active==="Expenses & Suppliers"&&<form className="entry-panel" onSubmit={createExpense}><div className="panel-heading"><div><h2>Record school expense</h2><p>Save as draft, then post when supporting documents are checked.</p></div><Plus size={18}/></div><div className="form-grid"><label>Description<input required value={form.description||""} onChange={e=>setField("description",e.target.value)}/></label><label>Expense category<select required value={form.category||""} onChange={e=>setField("category",e.target.value)}><option value="">Select category</option>{categories.filter(x=>x.is_active).map(x=><option value={x.id} key={x.id}>{x.name}</option>)}</select></label><label>Supplier (optional)<select value={form.supplier||""} onChange={e=>setField("supplier",e.target.value)}><option value="">No supplier selected</option>{suppliers.filter(x=>x.is_active).map(x=><option value={x.id} key={x.id}>{x.name}</option>)}</select></label><label>Financial period<select required value={form.period||""} onChange={e=>setField("period",e.target.value)}><option value="">Select period</option>{periods.filter(x=>!x.is_locked).map(x=><option value={x.id} key={x.id}>{x.name}</option>)}</select></label><label>Amount (KES)<input required type="number" min="0.01" step="0.01" value={form.amount||""} onChange={e=>setField("amount",e.target.value)}/></label><label>Paid through<select value={form.payment_method||"MPESA"} onChange={e=>setField("payment_method",e.target.value)}><option value="MPESA">M-Pesa</option><option value="CASH">Cash</option><option value="BANK">Bank</option></select></label><label>Expense date<input type="date" value={form.expense_date||today} onChange={e=>setField("expense_date",e.target.value)}/></label><label>Reference<input value={form.reference||""} onChange={e=>setField("reference",e.target.value)}/></label></div><button className="primary" disabled={busy||!categories.length||!periods.length}>Save expense draft</button>{(!categories.length||!periods.length)&&<small className="muted">Setup required: configure an expense category and financial period first.</small>}</form>}

        {canWrite&&active==="Settings"&&<div className="setup-grid">
          <form className="entry-panel" onSubmit={createAccount}><div className="panel-heading"><div><h2>Chart of accounts</h2><p>Create ledger accounts for this school.</p></div><Plus size={18}/></div><div className="form-grid"><label>Account code<input required value={form.account_code||""} onChange={e=>setField("account_code",e.target.value)}/></label><label>Account name<input required value={form.account_name||""} onChange={e=>setField("account_name",e.target.value)}/></label><label>Category<select value={form.account_category||"ASSET"} onChange={e=>setField("account_category",e.target.value)}>{["ASSET","LIABILITY","EQUITY","INCOME","EXPENSE"].map(x=><option key={x}>{x}</option>)}</select></label></div><button className="primary" disabled={busy}>Add account</button></form>
          <form className="entry-panel" onSubmit={createAcademicYear}><div className="panel-heading"><div><h2>Academic year</h2><p>Set the school's academic calendar.</p></div><Plus size={18}/></div><div className="form-grid"><label>Year name<input required value={form.year_name||""} onChange={e=>setField("year_name",e.target.value)} placeholder="2026"/></label><label>Start date<input type="date" required value={form.year_start||""} onChange={e=>setField("year_start",e.target.value)}/></label><label>End date<input type="date" required value={form.year_end||""} onChange={e=>setField("year_end",e.target.value)}/></label><label>Current academic year<select value={form.year_current||"true"} onChange={e=>setField("year_current",e.target.value)}><option value="true">Yes</option><option value="false">No</option></select></label></div><button className="primary" disabled={busy}>Add academic year</button></form>
          <form className="entry-panel" onSubmit={createPeriod}><div className="panel-heading"><div><h2>Financial period</h2><p>Set the posting dates for the school's books.</p></div><Plus size={18}/></div><div className="form-grid"><label>Period name<input required value={form.period_name||""} onChange={e=>setField("period_name",e.target.value)}/></label><label>Start date<input type="date" required value={form.period_start||""} onChange={e=>setField("period_start",e.target.value)}/></label><label>End date<input type="date" required value={form.period_end||""} onChange={e=>setField("period_end",e.target.value)}/></label></div><button className="primary" disabled={busy}>Add period</button></form>
          <form className="entry-panel" onSubmit={createFeeItem}><div className="panel-heading"><div><h2>Fee items</h2><p>Link each fee to an income account.</p></div><Plus size={18}/></div><div className="form-grid"><label>Fee code<input required value={form.fee_code||""} onChange={e=>setField("fee_code",e.target.value)}/></label><label>Fee name<input required value={form.fee_name||""} onChange={e=>setField("fee_name",e.target.value)}/></label><label>Income account<select required value={form.income_account||""} onChange={e=>setField("income_account",e.target.value)}><option value="">Select income account</option>{accounts.filter(x=>x.category==="INCOME"&&x.is_active).map(x=><option value={x.id} key={x.id}>{x.code} — {x.name}</option>)}</select></label></div><button className="primary" disabled={busy}>Add fee item</button></form>
          <form className="entry-panel" onSubmit={createExpenseCategory}><div className="panel-heading"><div><h2>Expense categories</h2><p>Map expense types to expense accounts.</p></div><Plus size={18}/></div><div className="form-grid"><label>Category code<input required value={form.expense_code||""} onChange={e=>setField("expense_code",e.target.value)}/></label><label>Category name<input required value={form.expense_name||""} onChange={e=>setField("expense_name",e.target.value)}/></label><label>Expense account<select required value={form.expense_account||""} onChange={e=>setField("expense_account",e.target.value)}><option value="">Select expense account</option>{accounts.filter(x=>x.category==="EXPENSE"&&x.is_active).map(x=><option value={x.id} key={x.id}>{x.code} — {x.name}</option>)}</select></label></div><button className="primary" disabled={busy}>Add expense category</button></form>
          <form className="entry-panel" onSubmit={saveBillingSettings}><div className="panel-heading"><div><h2>Billing account mappings</h2><p>Choose asset accounts for receivables and collections.</p></div><ShieldCheck size={18}/></div><div className="form-grid">{[["receivables_account","Student receivables"],["cash_account","Cash"],["bank_account","Bank"],["mpesa_account","M-Pesa clearing"]].map(([key,label])=><label key={key}>{label}<select required value={form[key]||String(billingSettings?.[key]||"")} onChange={e=>setField(key,e.target.value)}><option value="">Select asset account</option>{accounts.filter(x=>x.category==="ASSET"&&x.is_active).map(x=><option value={x.id} key={x.id}>{x.code} — {x.name}</option>)}</select></label>)}</div><div className="form-grid"><label>Invoice prefix<input value={form.invoice_prefix||billingSettings?.invoice_prefix||"INV"} onChange={e=>setField("invoice_prefix",e.target.value)}/></label><label>Receipt prefix<input value={form.receipt_prefix||billingSettings?.receipt_prefix||"RCT"} onChange={e=>setField("receipt_prefix",e.target.value)}/></label></div><button className="primary" disabled={busy||accounts.filter(x=>x.category==="ASSET").length<1}>Save billing settings</button></form>
        </div>}
\n
        {active==="Reports"&&<ReportPanel reportType={reportType} setReportType={setReportType} reportPeriod={reportPeriod} setReportPeriod={setReportPeriod} periods={periods} report={trialBalance} currency={school.currency}/>}
        {active==="General Ledger"&&<div className="notice"><ShieldCheck size={18}/><div><strong>Ledger controls active</strong><span>Accounts are school-scoped. Posted journals are immutable and must balance. Financial periods must be open when posting.</span></div></div>}
        {active==="Settings"&&<div className="notice"><Settings size={18}/><div><strong>Financial periods</strong><span>Only open periods can receive new postings. Period creation and billing-account setup are currently managed through authorised configuration endpoints.</span></div></div>}
        {loading?<div className="table-empty"><RefreshCw className="spin"/> Loading school records…</div>:<div className="data-panel"><div className="panel-heading"><div><h2>{active==="Overview"?"Recent financial activity":active==="Settings"?"Financial periods":active}</h2><p>{active==="Overview"?"Latest invoices, receipts and expenses recorded in this workspace.":"Records belonging to "+school.name+"."}</p></div><button className="secondary" onClick={()=>void loadData()}><RefreshCw size={15}/> Refresh</button></div>
          {active==="Audit Log"&&<DataTable rows={auditRows} currency={school.currency} empty="No audit events have been recorded yet." columns={columns}/>}{active!=="Reports"&&active!=="Audit Log"&&<DataTable rows={rows} currency={school.currency} empty="No records found. Add your first record using the form above." columns={columns}/>}
          {active==="Fees & Invoices"&&<div className="row-actions">{rows.filter(x=>x.status==="DRAFT").map(x=><button key={x.id} className="small-action" disabled={busy} onClick={()=>void issueInvoice(x.id)}>Issue {x.invoice_number}</button>)}</div>}
          {active==="Expenses & Suppliers"&&<div className="row-actions">{rows.filter(x=>x.status==="DRAFT").map(x=><button key={x.id} className="small-action" disabled={busy} onClick={()=>void postExpense(x.id)}>Post {x.expense_number}</button>)}</div>}
        </div>}
        <footer>PRECIOUS SCHOOLBOOKS <span>·</span> {school.name.toUpperCase()} <span>·</span> FINANCIAL RECORDS ARE LIVE FROM THE SCHOOL API</footer>
      </section>
    </main>
  </div>;
}
