import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, download } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Alert, Empty, Status, Ticket, fmtDate } from "../components/ui.jsx";

function Detail({ id, meta, onChange }) {
  const { user } = useAuth();
  const [q, setQ] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [rating, setRating] = useState(0);
  const [comments, setComments] = useState("");
  const [staff, setStaff] = useState([]);
  const [faq, setFaq] = useState(null);
  const [ok, setOk] = useState("");

  const load = () => api(`/queries/${id}`).then((x) => { setQ(x); setErr(""); }).catch((e) => { setQ(null); setErr(e.message); });
  useEffect(() => { setMsg(""); setFaq(null); setOk(""); load(); }, [id]);
  useEffect(() => { if (user.role === "admin") api("/admin/users?role=staff").then(setStaff).catch(() => {}); }, [user.role]);

  const run = async (fn) => {
    setErr(""); setOk("");
    try { setQ(await fn()); onChange(); } catch (e) { setErr(e.message); }
  };
  const reply = (e) => { e.preventDefault(); run(async () => { const r = await api(`/queries/${id}/replies`, { method: "POST", body: { message: msg } }); setMsg(""); return r; }); };
  const setStatus = (status) => run(() => api(`/queries/${id}/status`, { method: "PATCH", body: { status } }));
  const assign = (uid) => uid && run(() => api(`/admin/queries/${id}/assign`, { method: "PATCH", body: { assigned_to: Number(uid) } }));
  const sendFeedback = (e) => { e.preventDefault(); run(() => api(`/queries/${id}/feedback`, { method: "POST", body: { rating, comments } })); };
  const suggest = async (e) => {
    e.preventDefault();
    try { await api("/faqs", { method: "POST", body: faq }); setFaq(null); setOk(user.role === "admin" ? "Added to the knowledge base. Re-index to publish it." : "Suggestion sent to the administrator."); }
    catch (ex) { setErr(ex.message); }
  };

  if (!q) return err ? <Alert>{err}</Alert> : <p className="muted pad">Loading…</p>;
  const closed = q.status === "Closed";
  const next = (meta.transitions?.[q.status] || []).filter((s) => user.role === "admin" || ["In Progress", "Resolved"].includes(s));

  return (
    <div className="card detail">
      <div className="row between">
        <div><small className="muted">{q.ticket} · {q.category} · {q.department}</small><h2>{q.subject}</h2></div>
        <Status value={q.status} />
      </div>
      <p className="muted small">Raised by {q.student?.name} on {fmtDate(q.created_at)}{q.assignee ? ` · Handled by ${q.assignee.name}` : ""} · Priority {q.priority}</p>
      <p className="desc">{q.description}</p>
      {q.has_attachment && <button className="btn small" onClick={() => download(`/queries/${q.id}/attachment`, q.attachment_name || "attachment").catch((e) => setErr(e.message))}>Download {q.attachment_name}</button>}

      <h3>Conversation</h3>
      <div className="thread">
        {q.replies.length === 0 && <p className="muted">No replies yet.</p>}
        {q.replies.map((r) => (
          <div key={r.id} className={`reply ${r.author.role === "student" ? "student" : "staff"}`}>
            <b>{r.author.name}</b> <small className="muted">{fmtDate(r.created_at)}</small>
            <p>{r.message}</p>
          </div>
        ))}
      </div>

      {!closed && (
        <form onSubmit={reply} className="reply-box">
          <textarea rows={3} value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="Write a reply…" aria-label="Reply" required />
          <button className="btn primary" disabled={!msg.trim()}>Send reply</button>
        </form>
      )}

      {user.role !== "student" && !closed && (
        <div className="row wrap actions">
          {next.map((s) => <button key={s} className="btn" onClick={() => setStatus(s)}>Mark {s}</button>)}
          {user.role === "admin" && (
            <select value="" onChange={(e) => assign(e.target.value)} aria-label="Assign to staff">
              <option value="">Assign to staff…</option>
              {staff.map((s) => <option key={s.id} value={s.id}>{s.full_name} ({s.department})</option>)}
            </select>
          )}
        </div>
      )}

      {user.role === "student" && q.status === "Resolved" && !q.feedback && (
        <form className="feedback" onSubmit={sendFeedback}>
          <h3>Was this resolved to your satisfaction?</h3>
          <div className="stars" role="radiogroup" aria-label="Rating">
            {[1, 2, 3, 4, 5].map((n) => <button type="button" key={n} className={n <= rating ? "on" : ""} onClick={() => setRating(n)} aria-label={`${n} star${n > 1 ? "s" : ""}`}>★</button>)}
          </div>
          <input value={comments} onChange={(e) => setComments(e.target.value)} placeholder="Comments (optional)" />
          <button className="btn primary" disabled={!rating}>Submit feedback and close</button>
        </form>
      )}
      {q.feedback && <p className="notice">Rated {"★".repeat(q.feedback.rating)}{q.feedback.comments ? ` · “${q.feedback.comments}”` : ""}</p>}

      {user.role !== "student" && ["Resolved", "Closed"].includes(q.status) && !faq && (
        <button className="btn ghost" onClick={() => setFaq({ category: q.category, question: q.subject, answer: [...q.replies].reverse().find((r) => r.author.role !== "student")?.message || "" })}>Suggest as FAQ entry</button>
      )}
      {faq && (
        <form className="card inner" onSubmit={suggest}>
          <h3>Suggest FAQ entry</h3>
          <label>Question<input value={faq.question} onChange={(e) => setFaq({ ...faq, question: e.target.value })} required minLength={5} /></label>
          <label>Answer<textarea rows={3} value={faq.answer} onChange={(e) => setFaq({ ...faq, answer: e.target.value })} required /></label>
          <div className="row"><button className="btn primary">Send suggestion</button><button type="button" className="btn ghost" onClick={() => setFaq(null)}>Cancel</button></div>
        </form>
      )}
      {ok && <Alert kind="ok">{ok}</Alert>}
      <Alert>{err}</Alert>
    </div>
  );
}

export default function Queries() {
  const { id } = useParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const [list, setList] = useState([]);
  const [meta, setMeta] = useState({});
  const [f, setF] = useState({ status: "", category: "", search: "" });
  const [err, setErr] = useState("");

  const load = () => {
    const p = new URLSearchParams(Object.entries(f).filter(([, v]) => v));
    api(`/queries?${p}`).then(setList).catch((e) => setErr(e.message));
  };
  useEffect(() => { api("/meta").then(setMeta); }, []);
  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [f]);

  return (
    <>
      <h1>{user.role === "student" ? "My queries" : user.role === "staff" ? "Query inbox" : "All queries"}</h1>
      <div className="split">
        <section>
          <div className="filters">
            <input placeholder="Search subject or text" value={f.search} onChange={(e) => setF({ ...f, search: e.target.value })} />
            <select value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })} aria-label="Status">
              <option value="">All statuses</option>{(meta.statuses || []).map((s) => <option key={s}>{s}</option>)}
            </select>
            <select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })} aria-label="Category">
              <option value="">All categories</option>{(meta.categories || []).map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <Alert>{err}</Alert>
          {list.length === 0 ? (
            <Empty title="No queries match" hint={user.role === "student" ? "Raise one from the assistant or the Raise a query page." : "Nothing in this view right now."} />
          ) : (
            <div className="ticket-list">
              {list.map((q) => <Ticket key={q.id} q={q} active={String(q.id) === id} showStudent={user.role !== "student"} onClick={() => nav(`/queries/${q.id}`)} />)}
            </div>
          )}
        </section>
        <section>
          {id ? <Detail id={id} meta={meta} onChange={load} /> : <Empty title="Select a ticket" hint="Its conversation and actions appear here." />}
        </section>
      </div>
    </>
  );
}
