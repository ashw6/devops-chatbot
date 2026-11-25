from collections import Counter
from datetime import timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..common import serialize_query
from ..config import STATUSES
from ..database import get_db
from ..models import ChatLog, FAQEntry, Feedback, Notification, Query, User, now
from ..security import get_current_user, role_required
from .reports import build_report

router = APIRouter(prefix="/api", tags=["dashboard"])


def _scope(user: User, qs):
    if user.role == "student":
        return qs.filter(Query.student_id == user.id)
    if user.role == "staff":
        return qs.filter(Query.department_id == user.department_id)
    return qs


@router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    qs = _scope(user, db.query(Query))
    by_status = Counter(q.status for q in qs.all())
    open_total = sum(v for k, v in by_status.items() if k != "Closed")
    stats = [{"label": "Total queries", "value": sum(by_status.values())},
             {"label": "Open", "value": by_status["Open"] + by_status["Assigned"]},
             {"label": "In progress", "value": by_status["In Progress"]},
             {"label": "Resolved", "value": by_status["Resolved"] + by_status["Closed"]}]
    if user.role == "student":
        stats.append({"label": "Questions to the assistant",
                      "value": db.query(ChatLog).filter(ChatLog.user_id == user.id).count()})
    if user.role == "admin":
        stats += [{"label": "Users", "value": db.query(User).count()},
                  {"label": "Chatbot questions", "value": db.query(ChatLog).count()},
                  {"label": "FAQ suggestions to review",
                   "value": db.query(FAQEntry).filter(FAQEntry.status == "pending").count()}]
    recent = qs.order_by(Query.updated_at.desc()).limit(6).all()
    return {"stats": stats, "open_total": open_total, "recent": [serialize_query(q) for q in recent]}


@router.get("/analytics")
def analytics(user: User = Depends(role_required("admin", "staff")), db: Session = Depends(get_db)):
    qs = _scope(user, db.query(Query)).all()
    status = Counter(q.status for q in qs)
    cat = Counter(q.category for q in qs)
    out = {"by_status": [{"name": s, "value": status[s]} for s in STATUSES],
           "by_category": [{"name": k, "value": v} for k, v in cat.most_common()],
           "dept_performance": build_report("departments", db, user)["rows"],
           "chat_per_day": [], "avg_rating": None}
    ratings = db.query(func.avg(Feedback.rating)).join(Query, Query.id == Feedback.query_id)
    if user.role == "staff":
        ratings = ratings.filter(Query.department_id == user.department_id)
    avg = ratings.scalar()
    out["avg_rating"] = round(float(avg), 2) if avg else None
    if user.role == "admin":
        since = now() - timedelta(days=13)
        logs = db.query(ChatLog).filter(ChatLog.created_at >= since.replace(hour=0, minute=0, second=0)).all()
        for i in range(14):
            day = (since + timedelta(days=i)).date()
            day_logs = [l for l in logs if l.created_at.date() == day]
            out["chat_per_day"].append({"date": day.strftime("%d %b"), "questions": len(day_logs),
                                        "escalated": sum(1 for l in day_logs if l.escalated)})
    return out


@router.get("/notifications")
def notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = (db.query(Notification).filter(Notification.user_id == user.id)
             .order_by(Notification.id.desc()).limit(30).all())
    return {"unread": sum(1 for n in items if not n.is_read),
            "items": [{"id": n.id, "message": n.message, "query_id": n.query_id, "is_read": n.is_read,
                       "created_at": n.created_at.isoformat() + "Z"} for n in items]}


@router.post("/notifications/read")
def mark_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read.is_(False)) \
        .update({"is_read": True})
    db.commit()
    return {"ok": True}
