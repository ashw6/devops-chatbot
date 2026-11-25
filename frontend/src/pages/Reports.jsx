import { useEffect, useState } from "react";
import { api, download } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Alert, Empty } from "../components/ui.jsx";

const ALL = [["queries", "Query summary"], ["departments", "Department performance"], ["chatbot", "Chatbot usage"], ["unanswered", "Unanswered questions"]];

export default function Reports() {
  const { user } = useAuth();
  const reports = user.role === "admin" ? ALL : ALL.slice(0, 2);
  const [name, setName] = useState("queries");
  const [f, setF] = useState({ status: "", category: "", date_from: "", date_to: "" });
  const [meta, setMeta] = useState({});
  const [rep, setRep] = useState(null);
  const [err, setErr] = useState("");

  const qs = () => new URLSearchParams(Object.entries(f).filter(([, v]) => v)).toString();
  const load = () => api(`/reports/${name}?${qs()}`).then((r) => { setRep(r); setErr(""); }).catch((e) => setErr(e.message));
  useEffect(() => { api("/meta").then(setMeta); }, []);
  useEffect(() => { load(); }, [name, f]);
  const exp = (fmt) => download(`/reports/${name}/export?format=${fmt}&${qs()}`, `${name}-report.${fmt}`).catch((e) => setErr(e.message));

  return (
    <>
      <h1>Reports</h1>
      <div className="tabs">{reports.map(([k, label]) => <button key={k} className={name === k ? "on" : ""} onClick={() => setName(k)}>{label}</button>)}</div>
      {name === "queries" && (
        <div className="filters">
          <select value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })} aria-label="Status"><option value="">All statuses</option>{(meta.statuses || []).map((s) => <option key={s}>{s}</option>)}</select>
          <select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })} aria-label="Category"><option value="">All categories</option>{(meta.categories || []).map((s) => <option key={s}>{s}</option>)}</select>
          <label className="inline-label">From<input type="date" value={f.date_from} onChange={(e) => setF({ ...f, date_from: e.target.value })} /></label>
          <label className="inline-label">To<input type="date" value={f.date_to} onChange={(e) => setF({ ...f, date_to: e.target.value })} /></label>
        </div>
      )}
      <div className="row between wrap">
        <h2>{rep?.title}</h2>
        <div className="row"><button className="btn" onClick={() => exp("xlsx")}>Export Excel</button><button className="btn" onClick={() => exp("pdf")}>Export PDF</button></div>
      </div>
      <Alert>{err}</Alert>
      {rep && (rep.rows.length === 0 ? <Empty title="No data for this report" hint="Try widening the filters." /> : (
        <div className="table-wrap"><table>
          <thead><tr>{rep.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
          <tbody>{rep.rows.map((r, i) => <tr key={i}>{rep.columns.map((c) => <td key={c}>{r[c]}</td>)}</tr>)}</tbody>
        </table></div>
      ))}
    </>
  );
}
