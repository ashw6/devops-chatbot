import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Empty, Ticket } from "../components/ui.jsx";

export default function Dashboard() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => { api("/dashboard").then(setD).catch((e) => setErr(e.message)); }, []);
  const hello = user.full_name.split(" ")[0];
  return (
    <>
      <h1>Hello, {hello}</h1>
      <p className="lead">
        {user.role === "student" && "Ask the assistant first. If it can’t help, raise a query and track it here."}
        {user.role === "staff" && `Queries for ${user.department} appear here. Reply, resolve and suggest FAQs from repeat questions.`}
        {user.role === "admin" && "Everything across the college: queries, knowledge base, users and reports."}
      </p>
      {err && <div className="alert error">{err}</div>}
      {d && (
        <>
          <div className="stats">
            {d.stats.map((s) => (
              <div className="stat" key={s.label}><b>{s.value}</b><span>{s.label}</span></div>
            ))}
          </div>
          <div className="row between">
            <h2>Recent activity</h2>
            <div className="row">
              {user.role === "student" && <>
                <Link className="btn primary" to="/chat">Ask the assistant</Link>
                <Link className="btn" to="/raise">Raise a query</Link></>}
              {user.role !== "student" && <Link className="btn" to="/queries">Open all queries</Link>}
            </div>
          </div>
          {d.recent.length === 0 ? (
            <Empty title="No queries yet" hint={user.role === "student" ? "Try the assistant first. It answers most common questions in seconds." : "New queries for your scope will show up here."} />
          ) : (
            <div className="ticket-list">
              {d.recent.map((q) => <Ticket key={q.id} q={q} showStudent={user.role !== "student"} onClick={() => nav(`/queries/${q.id}`)} />)}
            </div>
          )}
        </>
      )}
    </>
  );
}
