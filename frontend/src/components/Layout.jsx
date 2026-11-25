import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { fmtDate } from "./ui.jsx";

const NAV = {
  student: [["/", "Home"], ["/chat", "Ask the assistant"], ["/raise", "Raise a query"], ["/queries", "My queries"]],
  staff: [["/", "Home"], ["/queries", "Query inbox"], ["/kb", "Suggest an FAQ"], ["/analytics", "Analytics"], ["/reports", "Reports"]],
  admin: [["/", "Home"], ["/queries", "All queries"], ["/kb", "Knowledge base"], ["/admin", "Users and departments"],
          ["/analytics", "Analytics"], ["/reports", "Reports"]],
};

function Bell() {
  const [data, setData] = useState({ unread: 0, items: [] });
  const [open, setOpen] = useState(false);
  const nav = useNavigate();
  const load = () => api("/notifications").then(setData).catch(() => {});
  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);
  const toggle = async () => {
    setOpen(!open);
    if (!open && data.unread) {
      await api("/notifications/read", { method: "POST" });
      setTimeout(load, 1500);
    }
  };
  return (
    <div className="bell">
      <button className="btn ghost" onClick={toggle} aria-label="Notifications">
        Updates{data.unread > 0 && <span className="dot">{data.unread}</span>}
      </button>
      {open && (
        <div className="popover">
          {data.items.length === 0 && <p className="muted pad">No updates yet.</p>}
          {data.items.map((n) => (
            <button key={n.id} className={`note ${n.is_read ? "" : "unread"}`}
              onClick={() => { setOpen(false); if (n.query_id) nav(`/queries/${n.query_id}`); }}>
              {n.message}
              <small>{fmtDate(n.created_at)}</small>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const [menu, setMenu] = useState(false);
  const nav = useNavigate();
  return (
    <div className="app">
      <aside className={`sidebar ${menu ? "open" : ""}`}>
        <div className="brand">
          <span className="mark">?</span>
          <div>
            <b>Campus Help Desk</b>
            <small>{user.role === "admin" ? "Administrator" : user.role === "staff" ? user.department + " staff" : "Student"}</small>
          </div>
        </div>
        <nav onClick={() => setMenu(false)}>
          {NAV[user.role].map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"}>{label}</NavLink>
          ))}
        </nav>
        <div className="me">
          <span>{user.full_name}</span>
          <small>{user.email}</small>
          <button className="btn ghost light" onClick={() => { logout(); nav("/login"); }}>Sign out</button>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <button className="btn ghost menu-btn" onClick={() => setMenu(!menu)}>Menu</button>
          <span className="spacer" />
          <Bell />
        </header>
        <main className="page"><Outlet /></main>
      </div>
    </div>
  );
}
