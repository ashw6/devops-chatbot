export const fmtDate = (s) =>
  s ? new Date(s).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "";

export function Status({ value }) {
  return <span className={`badge s-${value.toLowerCase().replace(" ", "-")}`}>{value}</span>;
}

export function Empty({ title, hint, children }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      {hint && <p>{hint}</p>}
      {children}
    </div>
  );
}

export function Alert({ kind = "error", children }) {
  return children ? <div className={`alert ${kind}`} role="alert">{children}</div> : null;
}

export function Ticket({ q, active, onClick, showStudent }) {
  return (
    <button className={`ticket ${active ? "active" : ""}`} onClick={onClick}>
      <span className="stub">
        <small>Ticket</small>
        <b>{q.ticket.replace("Q-", "")}</b>
      </span>
      <span className="body">
        <span className="t-subject">{q.subject}</span>
        <span className="t-meta">
          {q.category} · {q.department}
          {showStudent && q.student ? ` · ${q.student.name}` : ""}
        </span>
        <span className="t-foot">
          <Status value={q.status} />
          <small>{fmtDate(q.updated_at)}</small>
        </span>
      </span>
    </button>
  );
}
