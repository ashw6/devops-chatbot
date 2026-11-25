import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Alert, Empty, fmtDate } from "../components/ui.jsx";

const blank = { category: "Other", question: "", answer: "", source_doc: "", is_active: true };

export default function KnowledgeBase() {
  const { user } = useAuth();
  const admin = user.role === "admin";
  const [tab, setTab] = useState("faq");
  const [faqs, setFaqs] = useState([]);
  const [docs, setDocs] = useState([]);
  const [cats, setCats] = useState([]);
  const [form, setForm] = useState(null);
  const [msg, setMsg] = useState({ kind: "ok", text: "" });
  const [busy, setBusy] = useState(false);

  const say = (text, kind = "ok") => setMsg({ kind, text });
  const load = () => {
    api("/faqs").then(setFaqs).catch((e) => say(e.message, "error"));
    if (admin) api("/kb/documents").then(setDocs).catch(() => {});
  };
  useEffect(() => { load(); api("/meta").then((m) => setCats(m.categories)); }, []);

  const save = async (e) => {
    e.preventDefault();
    try {
      const body = { ...form, source_doc: form.source_doc || null };
      if (form.id) await api(`/faqs/${form.id}`, { method: "PUT", body });
      else await api("/faqs", { method: "POST", body });
      setForm(null); load();
      say(admin ? "Saved. Re-index to make the chatbot use it." : "Suggestion sent to the administrator.");
    } catch (ex) { say(ex.message, "error"); }
  };
  const approve = (f) => api(`/faqs/${f.id}`, { method: "PUT", body: { ...f, status: "approved", is_active: true } }).then(() => { load(); say("Approved. Re-index to publish."); }).catch((e) => say(e.message, "error"));
  const toggle = (f) => api(`/faqs/${f.id}`, { method: "PUT", body: { ...f, is_active: !f.is_active } }).then(load).catch((e) => say(e.message, "error"));
  const remove = (f) => window.confirm("Delete this FAQ entry?") && api(`/faqs/${f.id}`, { method: "DELETE" }).then(load).catch((e) => say(e.message, "error"));
  const reindex = async () => {
    setBusy(true);
    try { const r = await api("/kb/reindex", { method: "POST" }); say(`Index rebuilt: ${r.faq_entries} FAQ entries and ${r.documents} documents (${r.chunks} chunks).`); }
    catch (e) { say(e.message, "error"); } finally { setBusy(false); }
  };
  const upload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try { await api("/kb/upload", { method: "POST", form }); load(); say("Document uploaded. Re-index to include it."); }
    catch (ex) { say(ex.message, "error"); }
    e.target.value = "";
  };

  return (
    <>
      <div className="row between wrap">
        <h1>{admin ? "Knowledge base" : "Suggest an FAQ"}</h1>
        {admin && <button className="btn primary" onClick={reindex} disabled={busy}>{busy ? "Re-indexing…" : "Re-index knowledge base"}</button>}
      </div>
      <Alert kind={msg.kind}>{msg.text}</Alert>
      {admin && (
        <div className="tabs">
          <button className={tab === "faq" ? "on" : ""} onClick={() => setTab("faq")}>FAQ entries</button>
          <button className={tab === "docs" ? "on" : ""} onClick={() => setTab("docs")}>Documents</button>
        </div>
      )}

      {tab === "faq" && (
        <>
          {!form && <button className="btn" onClick={() => setForm({ ...blank })}>{admin ? "Add FAQ entry" : "Suggest a new entry"}</button>}
          {form && (
            <form className="card form" onSubmit={save}>
              <h3>{form.id ? "Edit entry" : admin ? "New FAQ entry" : "Suggest an entry"}</h3>
              <label>Category<select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>{cats.map((c) => <option key={c}>{c}</option>)}</select></label>
              <label>Question<input value={form.question} onChange={(e) => setForm({ ...form, question: e.target.value })} required minLength={5} /></label>
              <label>Answer<textarea rows={4} value={form.answer} onChange={(e) => setForm({ ...form, answer: e.target.value })} required /></label>
              <label>Source shown to students<input value={form.source_doc || ""} onChange={(e) => setForm({ ...form, source_doc: e.target.value })} placeholder="e.g. Fee Circular 2026" /></label>
              <div className="row"><button className="btn primary">Save</button><button type="button" className="btn ghost" onClick={() => setForm(null)}>Cancel</button></div>
            </form>
          )}
          {faqs.length === 0 ? <Empty title="No FAQ entries yet" hint="Add the first one to teach the assistant." /> : (
            <div className="table-wrap"><table>
              <thead><tr><th>Question</th><th>Category</th><th>Status</th>{admin && <th>Actions</th>}</tr></thead>
              <tbody>{faqs.map((f) => (
                <tr key={f.id}>
                  <td><b>{f.question}</b><br /><small className="muted">{f.answer.slice(0, 110)}{f.answer.length > 110 ? "…" : ""}</small></td>
                  <td>{f.category}</td>
                  <td>{f.status === "pending" ? <span className="badge s-open">Pending review</span> : f.is_active ? <span className="badge s-resolved">Active</span> : <span className="badge s-closed">Inactive</span>}</td>
                  {admin && <td className="row wrap">
                    {f.status === "pending" && <button className="btn small primary" onClick={() => approve(f)}>Approve</button>}
                    <button className="btn small" onClick={() => setForm(f)}>Edit</button>
                    <button className="btn small" onClick={() => toggle(f)}>{f.is_active ? "Deactivate" : "Activate"}</button>
                    <button className="btn small danger" onClick={() => remove(f)}>Delete</button>
                  </td>}
                </tr>))}
              </tbody></table></div>
          )}
        </>
      )}

      {tab === "docs" && admin && (
        <>
          <label className="upload">Upload a document (.txt, .md or .pdf)<input type="file" accept=".txt,.md,.pdf" onChange={upload} /></label>
          {docs.length === 0 ? <Empty title="No documents uploaded" hint="Upload circulars or prospectus text so the assistant can answer from them." /> : (
            <div className="table-wrap"><table>
              <thead><tr><th>File</th><th>Uploaded</th><th>Status</th><th>Actions</th></tr></thead>
              <tbody>{docs.map((d) => (
                <tr key={d.id}><td>{d.filename}</td><td>{fmtDate(d.uploaded_at)}</td>
                  <td>{d.is_active ? <span className="badge s-resolved">Active</span> : <span className="badge s-closed">Inactive</span>}</td>
                  <td className="row">
                    <button className="btn small" onClick={() => api(`/kb/documents/${d.id}`, { method: "PATCH" }).then(load)}>{d.is_active ? "Deactivate" : "Activate"}</button>
                    <button className="btn small danger" onClick={() => window.confirm("Delete this document?") && api(`/kb/documents/${d.id}`, { method: "DELETE" }).then(load)}>Delete</button>
                  </td></tr>))}
              </tbody></table></div>
          )}
        </>
      )}
    </>
  );
}
