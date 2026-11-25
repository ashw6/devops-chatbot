import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { Alert } from "../components/ui.jsx";

const DEMO = [
  ["Student", "student@college.edu", "Student@123"],
  ["Accounts staff", "staff.accounts@college.edu", "Staff@123"],
  ["Administrator", "admin@college.edu", "Admin@123"],
];

export default function Login() {
  const { login, register } = useAuth();
  const nav = useNavigate();
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ full_name: "", email: "", password: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      if (mode === "login") await login(f.email, f.password);
      else await register(f.full_name, f.email, f.password);
      nav("/");
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <section className="login-art">
        <h1>Ask once.<br />Get it answered.</h1>
        <p>Fees, exams, hostel, certificates. The assistant answers from official college documents, and anything it can’t answer becomes a ticket that someone owns.</p>
        <div className="stubs" aria-hidden="true">
          <div className="ticket demo"><span className="stub"><small>Ticket</small><b>00127</b></span>
            <span className="body"><span className="t-subject">Bonafide certificate for bank loan</span><span className="t-meta">Certificates · Administration</span></span></div>
        </div>
      </section>
      <form className="login-form" onSubmit={submit}>
        <div className="tabs">
          <button type="button" className={mode === "login" ? "on" : ""} onClick={() => setMode("login")}>Sign in</button>
          <button type="button" className={mode === "register" ? "on" : ""} onClick={() => setMode("register")}>Create student account</button>
        </div>
        {mode === "register" && (
          <label>Full name<input value={f.full_name} onChange={set("full_name")} required minLength={2} /></label>
        )}
        <label>Email<input type="email" value={f.email} onChange={set("email")} required autoComplete="email" /></label>
        <label>Password<input type="password" value={f.password} onChange={set("password")} required minLength={mode === "register" ? 8 : 1}
          autoComplete={mode === "login" ? "current-password" : "new-password"} />
          {mode === "register" && <small className="muted">At least 8 characters.</small>}
        </label>
        <Alert>{err}</Alert>
        <button className="btn primary wide" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button>
        {mode === "login" && (
          <div className="demo-box">
            <small className="muted">Demo accounts (development data)</small>
            {DEMO.map(([label, email, password]) => (
              <button type="button" key={email} className="btn ghost" onClick={() => setF({ ...f, email, password })}>{label}</button>
            ))}
          </div>
        )}
      </form>
    </div>
  );
}
