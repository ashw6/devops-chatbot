import io
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import ChatLog, Department, Query, User
from ..security import role_required

router = APIRouter(prefix="/api/reports", tags=["reports"])
NAMES = ("queries", "departments", "chatbot", "unanswered")


def _date(value: str | None, end=False):
    if not value:
        return None
    try:
        d = datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(400, "Dates must look like 2026-08-31")
    return d + timedelta(days=1) if end else d


def _scoped_queries(db: Session, user: User):
    qs = db.query(Query)
    return qs.filter(Query.department_id == user.department_id) if user.role == "staff" else qs


def _fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


def build_report(name: str, db: Session, user: User, status=None, category=None, date_from=None, date_to=None):
    if name not in NAMES:
        raise HTTPException(404, "Unknown report")
    if user.role == "staff" and name in ("chatbot", "unanswered"):
        raise HTTPException(403, "Access denied")
    start, end = _date(date_from), _date(date_to, end=True)

    if name == "queries":
        qs = _scoped_queries(db, user)
        if status:
            qs = qs.filter(Query.status == status)
        if category:
            qs = qs.filter(Query.category == category)
        if start:
            qs = qs.filter(Query.created_at >= start)
        if end:
            qs = qs.filter(Query.created_at < end)
        cols = ["Ticket", "Student", "Category", "Department", "Status", "Priority", "Created", "Resolved"]
        rows = [{"Ticket": f"Q-{q.id:05d}", "Student": q.student.full_name, "Category": q.category,
                 "Department": q.department.name if q.department else "", "Status": q.status,
                 "Priority": q.priority, "Created": _fmt(q.created_at), "Resolved": _fmt(q.resolved_at)}
                for q in qs.order_by(Query.id.desc()).all()]
        return {"title": "Query Summary Report", "columns": cols, "rows": rows, "summary": {"Total queries": len(rows)}}

    if name == "departments":
        depts = db.query(Department).order_by(Department.name)
        if user.role == "staff":
            depts = depts.filter(Department.id == user.department_id)
        by_dept = defaultdict(list)
        for q in db.query(Query).all():
            by_dept[q.department_id].append(q)
        cols = ["Department", "Received", "Resolved", "Pending", "Avg resolution (hours)"]
        rows = []
        for d in depts:
            qs = by_dept.get(d.id, [])
            done = [q for q in qs if q.status in ("Resolved", "Closed")]
            hrs = [(q.resolved_at - q.created_at).total_seconds() / 3600 for q in done if q.resolved_at]
            rows.append({"Department": d.name, "Received": len(qs), "Resolved": len(done),
                         "Pending": len(qs) - len(done),
                         "Avg resolution (hours)": round(sum(hrs) / len(hrs), 1) if hrs else 0})
        return {"title": "Department Performance Report", "columns": cols, "rows": rows, "summary": {}}

    logs = db.query(ChatLog)
    if start:
        logs = logs.filter(ChatLog.created_at >= start)
    if end:
        logs = logs.filter(ChatLog.created_at < end)
    logs = logs.all()

    if name == "chatbot":
        sessions = len({(l.user_id, l.created_at.date()) for l in logs})
        escalated = sum(1 for l in logs if l.escalated)
        topics = Counter((l.sources or "").split("|")[0] for l in logs if not l.escalated and l.sources)
        rows = [{"Metric": "Chat sessions", "Value": sessions},
                {"Metric": "Questions asked", "Value": len(logs)},
                {"Metric": "Answered with high confidence", "Value": len(logs) - escalated},
                {"Metric": "Escalated / not answered", "Value": escalated}]
        rows += [{"Metric": f"Top topic: {t}", "Value": n} for t, n in topics.most_common(8)]
        return {"title": "Chatbot Usage Report", "columns": ["Metric", "Value"], "rows": rows,
                "summary": {"Questions": len(logs), "Escalated": escalated}}

    counts, last = Counter(), {}
    for l in logs:
        if l.escalated:
            key = l.user_question.strip().lower()
            counts[key] += 1
            last[key] = max(last.get(key, l.created_at), l.created_at)
    rows = [{"Question": k, "Times asked": n, "Last asked": _fmt(last[k])} for k, n in counts.most_common(100)]
    return {"title": "Unanswered Questions Report", "columns": ["Question", "Times asked", "Last asked"],
            "rows": rows, "summary": {"Distinct questions": len(rows)}}


@router.get("/{name}")
def report(name: str, status: str | None = None, category: str | None = None, date_from: str | None = None,
           date_to: str | None = None, user: User = Depends(role_required("admin", "staff")),
           db: Session = Depends(get_db)):
    return build_report(name, db, user, status, category, date_from, date_to)


@router.get("/{name}/export")
def export(name: str, format: str = "xlsx", status: str | None = None, category: str | None = None,
           date_from: str | None = None, date_to: str | None = None,
           user: User = Depends(role_required("admin", "staff")), db: Session = Depends(get_db)):
    rep = build_report(name, db, user, status, category, date_from, date_to)
    cols, rows = rep["columns"], rep["rows"]
    if format == "xlsx":
        from openpyxl import Workbook
        from openpyxl.styles import Font
        wb = Workbook()
        ws = wb.active
        ws.title = name[:30]
        ws.append(cols)
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in rows:
            ws.append([r[c] for c in cols])
        for i, c in enumerate(cols, 1):
            ws.column_dimensions[ws.cell(1, i).column_letter].width = max(14, min(60, len(c) + 6))
        buf = io.BytesIO()
        wb.save(buf)
        return Response(buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="{name}-report.xlsx"'})
    if format == "pdf":
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
        styles = getSampleStyleSheet()
        cell = styles["BodyText"]
        cell.fontSize = 8
        data = [cols] + [[Paragraph(str(r[c]), cell) for c in cols] for r in rows]
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10284A")),
                                   ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTSIZE", (0, 0), (-1, -1), 8),
                                   ("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        doc.build([Paragraph(rep["title"], styles["Title"]),
                   Paragraph(f"Generated {datetime.utcnow():%Y-%m-%d %H:%M} UTC", styles["Normal"]),
                   Spacer(1, 10), table])
        return Response(buf.getvalue(), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{name}-report.pdf"'})
    raise HTTPException(400, "format must be xlsx or pdf")
