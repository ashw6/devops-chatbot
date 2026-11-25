from fastapi import HTTPException
from sqlalchemy.orm import Session
from .models import Notification, Query, User


def notify(db: Session, user_id: int | None, message: str, query_id: int | None = None):
    if user_id:
        db.add(Notification(user_id=user_id, message=message, query_id=query_id))


def notify_department(db: Session, department_id: int | None, message: str, query_id: int | None = None):
    if not department_id:
        return
    for u in db.query(User).filter(User.department_id == department_id, User.role == "staff",
                                   User.is_active.is_(True)):
        notify(db, u.id, message, query_id)


def ticket(q: Query) -> str:
    return f"Q-{q.id:05d}"


def iso(dt):
    return dt.isoformat() + "Z" if dt else None


def user_brief(u: User | None):
    return {"id": u.id, "name": u.full_name, "role": u.role} if u else None


def serialize_user(u: User):
    return {"id": u.id, "full_name": u.full_name, "email": u.email, "role": u.role,
            "department_id": u.department_id, "department": u.department.name if u.department else None,
            "is_active": u.is_active, "created_at": iso(u.created_at)}


def serialize_query(q: Query, detail: bool = False):
    d = {"id": q.id, "ticket": ticket(q), "category": q.category, "subject": q.subject, "status": q.status,
         "priority": q.priority, "department": q.department.name if q.department else None,
         "department_id": q.department_id, "student": user_brief(q.student), "assignee": user_brief(q.assignee),
         "created_at": iso(q.created_at), "updated_at": iso(q.updated_at), "resolved_at": iso(q.resolved_at),
         "has_attachment": bool(q.attachment_path)}
    if detail:
        d.update({
            "description": q.description, "attachment_name": q.attachment_name, "chat_log_id": q.chat_log_id,
            "replies": [{"id": r.id, "message": r.message, "created_at": iso(r.created_at),
                         "author": user_brief(r.author)} for r in q.replies],
            "feedback": ({"rating": q.feedback.rating, "comments": q.feedback.comments}
                         if q.feedback else None),
        })
    return d


def check_query_access(user: User, q: Query | None) -> Query:
    """Ownership / department filters (TC-16, TC-17)."""
    if q is None:
        raise HTTPException(404, "Query not found")
    if user.role == "student" and q.student_id != user.id:
        raise HTTPException(404, "Query not found")
    if user.role == "staff" and q.department_id != user.department_id:
        raise HTTPException(403, "Access denied")
    return q
