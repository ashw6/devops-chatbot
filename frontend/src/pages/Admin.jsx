import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Alert } from "../components/ui.jsx";

export default function Admin() {
  const { user: me } = useAuth();
  const [tab, setTab] = useState("users");
  const [users, setUsers] = useState([]);
  const [depts, setDepts] = useState([]);
  const [nu, setNu] = useState({ full_name: "", email: "", password: "", role: "staff", department_id: "" });
  const [dn, setDn] = useState("");
  const [msg, setMsg] = useState({ kind: "ok", text: "" });
  const say = (text, kind = "ok") => setMsg({ kind, text });

  const load = () => {
    api("/admin/users").then(setUsers).catch((e) => say(e.message, "error"));
    api("/departments").then((d) => { setDepts(d); setNu((x) => ({ ...x, department_id: x.department_id || d[0]?.id || "" })); });
  };
  useEffect(load, []);

  const patch = (u, body) => api(`/admin/users/${u.id}`, { method: "PATCH", body }).then(load).catch((e) => say(e.message, "error"));
  const create = async (e) => {
    e.preventDefault();
    try {
      await api("/admin/users", { method: "POST", body: { ...nu, department_id: nu.role === "staff" ? Number(nu.department_id) : null } });
      setNu({ ...nu, full_name: "", email: "", password: "" });
      say("User created."); load();
    } catch (ex) { say(ex.message, "error"); }
  };
  const addDept = async (e) => {
    e.preventDefault();
    try { await api("/admin/departments", { method: "POST", body: { name: dn } }); setDn(""); say("Department added."); load(); }
    catch (ex) { say(ex.message, "error"); }
  };
  const setHead = (d, head) => api(`/admin/departments/${d.id}`, { method: "PUT", body: { name: d.name, head_user_id: head ? Number(head) : null } }).then(load).catch((e) => say(e.message, "error"));

  return (
    <>
      <h1>Users and departments</h1>
      <Alert kind={msg.kind}>{msg.text}</Alert>
      <div className="tabs">
        <button className={tab === "users" ? "on" : ""} onClick={() => setTab("users")}>Users</button>
        <button className={tab === "depts" ? "on" : ""} onClick={() => setTab("depts")}>Departments</button>
      </div>
      {tab === "users" && (
        <>
          <form className="card form inline" onSubmit={create}>
            <h3>Add a user</h3>
            <input placeholder="Full name" value={nu.full_name} onChange={(e) => setNu({ ...nu, full_name: e.target.value })} required />
            <input type="email" placeholder="Email" value={nu.email} onChange={(e) => setNu({ ...nu, email: e.target.value })} required />
            <input type="password" placeholder="Temporary password (8+)" value={nu.password} onChange={(e) => setNu({ ...nu, password: e.target.value })} required minLength={8} />
            <select value={nu.role} onChange={(e) => setNu({ ...nu, role: e.target.value })} aria-label="Role"><option value="staff">Staff</option><option value="admin">Administrator</option><option value="student">Student</option></select>
            {nu.role === "staff" && <select value={nu.department_id} onChange={(e) => setNu({ ...nu, department_id: e.target.value })} aria-label="Department">{depts.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select>}
            <button className="btn primary">Add user</button>
          </form>
          <div className="table-wrap"><table>
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Department</th><th>Status</th></tr></thead>
            <tbody>{users.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name}</td><td>{u.email}</td>
                <td><select value={u.role} disabled={u.id === me.id} onChange={(e) => patch(u, { role: e.target.value })} aria-label={`Role of ${u.full_name}`}><option value="student">student</option><option value="staff">staff</option><option value="admin">admin</option></select></td>
                <td>{u.role === "staff" ? <select value={u.department_id || ""} onChange={(e) => patch(u, { department_id: Number(e.target.value) })} aria-label={`Department of ${u.full_name}`}><option value="" disabled>Choose…</option>{depts.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select> : "–"}</td>
                <td><button className={`btn small ${u.is_active ? "" : "danger"}`} disabled={u.id === me.id} onClick={() => patch(u, { is_active: !u.is_active })}>{u.is_active ? "Active" : "Disabled"}</button></td>
              </tr>))}
            </tbody></table></div>
        </>
      )}
      {tab === "depts" && (
        <>
          <form className="card form inline" onSubmit={addDept}>
            <h3>Add a department</h3>
            <input placeholder="Department name" value={dn} onChange={(e) => setDn(e.target.value)} required minLength={2} />
            <button className="btn primary">Add</button>
          </form>
          <div className="table-wrap"><table>
            <thead><tr><th>Department</th><th>Head</th><th>Staff</th></tr></thead>
            <tbody>{depts.map((d) => {
              const staff = users.filter((u) => u.role === "staff" && u.department_id === d.id);
              return <tr key={d.id}><td><b>{d.name}</b></td>
                <td><select value={d.head_user_id || ""} onChange={(e) => setHead(d, e.target.value)} aria-label={`Head of ${d.name}`}><option value="">Not set</option>{staff.map((s) => <option key={s.id} value={s.id}>{s.full_name}</option>)}</select></td>
                <td>{staff.length}</td></tr>;
            })}</tbody></table></div>
        </>
      )}
    </>
  );
}
