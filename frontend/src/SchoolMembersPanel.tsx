import { FormEvent, useEffect, useState } from "react";
import { api } from "./api";

type Member = { id:number; user_id:number; username:string; email:string; first_name:string; last_name:string; role:string; is_active:boolean; created_at:string };
type Props = { schoolId:number; requesterRole:string };

export default function SchoolMembersPanel({ schoolId, requesterRole }: Props) {
  const [members,setMembers] = useState<Member[]>([]);
  const [form,setForm] = useState({username:"",email:"",first_name:"",last_name:"",password:"",role:"BURSAR"});
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [success,setSuccess] = useState("");
  const owner = requesterRole==="OWNER";
  const roleOptions = owner ? ["OWNER","ADMIN","ACCOUNTANT","BURSAR","VIEWER"] : ["ACCOUNTANT","BURSAR","VIEWER"];

  async function load() {
    try { setMembers(await api<Member[]>(`/api/schools/${schoolId}/members/`)); }
    catch(e) { setError(e instanceof Error ? e.message : "Unable to load school users."); }
  }
  useEffect(() => { void load(); }, [schoolId]);

  async function submit(event:FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setSuccess("");
    try {
      await api(`/api/schools/${schoolId}/members/`,{method:"POST",body:JSON.stringify(form)});
      setForm({username:"",email:"",first_name:"",last_name:"",password:"",role:"BURSAR"});
      setSuccess("School user created."); await load();
    } catch(e) { setError(e instanceof Error ? e.message : "Unable to create user."); }
    finally { setBusy(false); }
  }

  async function update(member:Member, changes:Partial<Member>) {
    setBusy(true); setError(""); setSuccess("");
    try {
      await api(`/api/schools/${schoolId}/members/${member.id}/`,{method:"PATCH",body:JSON.stringify(changes)});
      setSuccess("User access updated."); await load();
    } catch(e) { setError(e instanceof Error ? e.message : "Unable to update user."); }
    finally { setBusy(false); }
  }

  return <div className="data-panel members-panel">
    <div className="panel-heading"><div><h2>School user access</h2><p>Create staff logins and manage their access to this school's records.</p></div></div>
    {error&&<div className="error-banner">{error}</div>}{success&&<div className="success-banner">{success}</div>}
    <form className="entry-panel" onSubmit={submit}>
      <div className="form-grid">
        <label>Username<input required value={form.username} onChange={e=>setForm(v=>({...v,username:e.target.value}))}/></label>
        <label>Email<input type="email" value={form.email} onChange={e=>setForm(v=>({...v,email:e.target.value}))}/></label>
        <label>First name<input value={form.first_name} onChange={e=>setForm(v=>({...v,first_name:e.target.value}))}/></label>
        <label>Last name<input value={form.last_name} onChange={e=>setForm(v=>({...v,last_name:e.target.value}))}/></label>
        <label>Temporary password<input type="password" minLength={8} required value={form.password} onChange={e=>setForm(v=>({...v,password:e.target.value}))}/></label>
        <label>School role<select value={form.role} onChange={e=>setForm(v=>({...v,role:e.target.value}))}>{roleOptions.map(role=><option key={role} value={role}>{role}</option>)}</select></label>
      </div>
      <button className="primary" disabled={busy}>Create school login</button>
    </form>
    <div className="table-wrap"><table><thead><tr><th>User</th><th>Email</th><th>Role</th><th>Status</th><th>Access</th></tr></thead><tbody>
      {members.map(member=><tr key={member.id}>
        <td>{member.first_name||member.last_name ? (member.first_name+" "+member.last_name).trim() : member.username}<small className="member-username">{member.username}</small></td>
        <td>{member.email||"—"}</td>
        <td><select disabled={busy||(!owner&&["OWNER","ADMIN"].includes(member.role))} value={member.role} onChange={e=>void update(member,{role:e.target.value})}>{roleOptions.map(role=><option key={role} value={role}>{role}</option>)}</select></td>
        <td>{member.is_active?"Active":"Inactive"}</td>
        <td><button className="small-action" disabled={busy||(!owner&&["OWNER","ADMIN"].includes(member.role))} onClick={()=>void update(member,{is_active:!member.is_active})}>{member.is_active?"Deactivate":"Reactivate"}</button></td>
      </tr>)}
      {!members.length&&<tr><td colSpan={5}>No school users found.</td></tr>}
    </tbody></table></div>
    <p className="muted report-note">Share temporary passwords securely and ask staff to change them after first sign-in. Administrators cannot create or modify owner and administrator accounts.</p>
  </div>;
}
