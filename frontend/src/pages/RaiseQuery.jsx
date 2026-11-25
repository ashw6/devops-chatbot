import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { Alert } from "../components/ui.jsx";

export default function RaiseQuery() {
  const nav = useNavigate();
  const pre = useLocation().state || {};
  const [meta, setMeta] = useState({ categories: [], priorities: [] });
  const [f, setF] = useState({ category: "", subject: pre.subject || "", description: pre.description || "", priority: "Normal" });
  const [file, setFile] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { api("/meta").then((m) => { setMeta(m); setF((x) => ({ ...x, category: x.category || m.categories[0] })); }); }, []);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    const form = new FormData();
    Object.entries(f).forEach(([k, v]) => form.append(k, v));
    if (pre.chat_log_id) form.append("chat_log_id", pre.chat_log_id);
    if (file) form.append("file", file);
    try {
      const q = await api("/queries", { method: "POST", form });
      nav(`/queries/${q.id}`);
    } catch (ex) { setErr(ex.message); } finally { setBusy(false); }
  };

  return (
    <form className="card form narrow" onSubmit={submit}>
      <h1>Raise a query</h1>
      {pre.chat_log_id && <p className="lead">We copied your question from the assistant so staff can see what you already asked.</p>}
      <div className="two">
        <label>Category
          <select value={f.category} onChange={set("category")}>{meta.categories.map((c) => <option key={c}>{c}</option>)}</select>
        </label>
        <label>Priority
          <select value={f.priority} onChange={set("priority")}>{meta.priorities.map((c) => <option key={c}>{c}</option>)}</select>
        </label>
      </div>
      <label>Subject<input value={f.subject} onChange={set("subject")} maxLength={200} required /></label>
      <label>Describe your problem<textarea rows={6} value={f.description} onChange={set("description")} required /></label>
      <label>Attachment (optional)
        <input type="file" accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.txt" onChange={(e) => setFile(e.target.files[0] || null)} />
        <small className="muted">PDF, image, Word or text file, up to 5 MB.</small>
      </label>
      <Alert>{err}</Alert>
      <button className="btn primary" disabled={busy}>{busy ? "Submitting…" : "Submit query"}</button>
    </form>
  );
}
