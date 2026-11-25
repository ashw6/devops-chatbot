import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Alert } from "../components/ui.jsx";

const NAVY = "#10284A", TEAL = "#0B7F7A", GOLD = "#E8A317";

function Chart({ title, children, empty }) {
  return <div className="card chart"><h3>{title}</h3>{empty ? <p className="muted">Not enough data yet.</p> : <ResponsiveContainer width="100%" height={260}>{children}</ResponsiveContainer>}</div>;
}

export default function Analytics() {
  const { user } = useAuth();
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => { api("/analytics").then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return <Alert>{err}</Alert>;
  if (!d) return <p className="muted pad">Loading…</p>;
  const noQueries = d.by_status.every((s) => s.value === 0);
  return (
    <>
      <h1>Analytics</h1>
      <p className="lead">{user.role === "staff" ? `Showing ${user.department} only.` : "All departments."}
        {d.avg_rating && ` Average feedback rating: ${d.avg_rating} / 5.`}</p>
      <div className="charts">
        <Chart title="Queries by status" empty={noQueries}>
          <BarChart data={d.by_status}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" fontSize={12} /><YAxis allowDecimals={false} fontSize={12} /><Tooltip /><Bar dataKey="value" name="Queries" fill={NAVY} radius={[4, 4, 0, 0]} /></BarChart>
        </Chart>
        <Chart title="Queries by category" empty={d.by_category.length === 0}>
          <BarChart data={d.by_category} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" allowDecimals={false} fontSize={12} /><YAxis type="category" dataKey="name" width={90} fontSize={12} /><Tooltip /><Bar dataKey="value" name="Queries" fill={TEAL} radius={[0, 4, 4, 0]} /></BarChart>
        </Chart>
        <Chart title="Resolution time by department (hours)" empty={d.dept_performance.length === 0}>
          <BarChart data={d.dept_performance}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="Department" fontSize={12} /><YAxis fontSize={12} /><Tooltip /><Bar dataKey="Avg resolution (hours)" fill={GOLD} radius={[4, 4, 0, 0]} /></BarChart>
        </Chart>
        {user.role === "admin" && (
          <Chart title="Chatbot questions, last 14 days" empty={d.chat_per_day.every((x) => x.questions === 0)}>
            <LineChart data={d.chat_per_day}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="date" fontSize={11} /><YAxis allowDecimals={false} fontSize={12} /><Tooltip /><Legend />
              <Line type="monotone" dataKey="questions" name="Questions" stroke={NAVY} strokeWidth={2} dot={false} /><Line type="monotone" dataKey="escalated" name="Not answered" stroke={GOLD} strokeWidth={2} dot={false} /></LineChart>
          </Chart>
        )}
      </div>
    </>
  );
}
