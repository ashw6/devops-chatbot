import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
from ..common import check_query_access, notify, notify_department, serialize_query, ticket
from ..config import CATEGORIES, CATEGORY_DEPARTMENT, PRIORITIES, STATUSES, TRANSITIONS, settings
from ..database import get_db
from ..models import ChatLog, Department, Feedback, Query, QueryReply, User, now
from ..security import get_current_user, role_required

router = APIRouter(prefix="/api/queries", tags=["queries"])
ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".txt"}
STAFF_SETTABLE = {"In Progress", "Resolved"}


class ReplyIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class StatusIn(BaseModel):
    status: str


class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comments: str | None = Field(default=None, max_length=1000)


@router.post("", status_code=201)
async def create_query(category: str = Form(...), subject: str = Form(...), description: str = Form(...),
                       priority: str = Form("Normal"), chat_log_id: int | None = Form(None),
                       file: UploadFile | None = File(None),
                       user: User = Depends(role_required("student")), db: Session = Depends(get_db)):
    subject, description = subject.strip(), description.strip()
    if not subject or not description:
        raise HTTPException(400, "Subject and description are required")
    if category not in CATEGORIES:
        raise HTTPException(400, "Unknown category")
    if priority not in PRIORITIES:
        priority = "Normal"
    path = name = None
    if file is not None and file.filename:
        ext = Path(file.filename).suffix.lower()
        data = await file.read()
        if ext not in ALLOWED_EXT:
            raise HTTPException(400, "File type not allowed")
        if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(400, f"File is larger than {settings.MAX_UPLOAD_MB} MB")
        path = f"{uuid.uuid4().hex}{ext}"
        (settings.UPLOAD_DIR / path).write_bytes(data)
        name = Path(file.filename).name[:200]
    if chat_log_id and not db.query(ChatLog).filter(ChatLog.id == chat_log_id, ChatLog.user_id == user.id).first():
        chat_log_id = None
    dept = db.query(Department).filter(Department.name == CATEGORY_DEPARTMENT[category]).first()
    q = Query(student_id=user.id, department_id=dept.id if dept else None, category=category, subject=subject,
              description=description, priority=priority, attachment_path=path, attachment_name=name,
              chat_log_id=chat_log_id)
    db.add(q)
    db.flush()
    notify_department(db, q.department_id, f"New query {ticket(q)}: {subject}", q.id)
    db.commit()
    return serialize_query(q, detail=True)


@router.get("")
def list_queries(status: str | None = None, category: str | None = None, search: str | None = None,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    qs = db.query(Query)
    if user.role == "student":
        qs = qs.filter(Query.student_id == user.id)
    elif user.role == "staff":
        qs = qs.filter(Query.department_id == user.department_id)
    if status in STATUSES:
        qs = qs.filter(Query.status == status)
    if category:
        qs = qs.filter(Query.category == category)
    if search:
        like = f"%{search.strip()}%"
        qs = qs.filter(or_(Query.subject.ilike(like), Query.description.ilike(like)))
    return [serialize_query(q) for q in qs.order_by(Query.updated_at.desc()).limit(500).all()]


@router.get("/{query_id}")
def get_query(query_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = check_query_access(user, db.get(Query, query_id))
    return serialize_query(q, detail=True)


@router.get("/{query_id}/attachment")
def attachment(query_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = check_query_access(user, db.get(Query, query_id))
    if not q.attachment_path:
        raise HTTPException(404, "No attachment")
    return FileResponse(settings.UPLOAD_DIR / q.attachment_path, filename=q.attachment_name)


@router.post("/{query_id}/replies", status_code=201)
def add_reply(query_id: int, body: ReplyIn, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    q = check_query_access(user, db.get(Query, query_id))
    if q.status == "Closed":
        raise HTTPException(409, "This query is closed and can no longer be changed")
    message = body.message.strip()
    if not message:
        raise HTTPException(400, "Reply cannot be empty")
    db.add(QueryReply(query_id=q.id, author_id=user.id, message=message))
    if user.role == "student":
        if q.status == "Resolved":
            q.status, q.resolved_at = "In Progress", None
        if q.assigned_to:
            notify(db, q.assigned_to, f"Student replied on {ticket(q)}", q.id)
        else:
            notify_department(db, q.department_id, f"Student replied on {ticket(q)}", q.id)
    else:
        if q.status in ("Open", "Assigned"):
            q.status = "In Progress"
        if not q.assigned_to and user.role == "staff":
            q.assigned_to = user.id
        notify(db, q.student_id, f"New reply on {ticket(q)}: {q.subject}", q.id)
    q.updated_at = now()
    db.commit()
    return serialize_query(q, detail=True)


@router.patch("/{query_id}/status")
def change_status(query_id: int, body: StatusIn, user: User = Depends(role_required("staff", "admin")),
                  db: Session = Depends(get_db)):
    q = check_query_access(user, db.get(Query, query_id))
    if q.status == "Closed":
        raise HTTPException(409, "This query is closed and can no longer be changed")
    if body.status not in STATUSES:
        raise HTTPException(400, "Unknown status")
    if body.status not in TRANSITIONS[q.status]:
        raise HTTPException(400, f"Invalid transition: {q.status} to {body.status}")
    if user.role == "staff" and body.status not in STAFF_SETTABLE:
        raise HTTPException(403, "Staff can only set In Progress or Resolved")
    q.status = body.status
    q.resolved_at = now() if body.status == "Resolved" else None
    if user.role == "staff" and not q.assigned_to:
        q.assigned_to = user.id
    msg = f"{ticket(q)} is now {q.status}"
    if q.status == "Resolved":
        msg += ". Please rate the answer."
    notify(db, q.student_id, msg, q.id)
    db.commit()
    return serialize_query(q, detail=True)


@router.post("/{query_id}/feedback", status_code=201)
def feedback(query_id: int, body: FeedbackIn, user: User = Depends(role_required("student")),
             db: Session = Depends(get_db)):
    q = check_query_access(user, db.get(Query, query_id))
    if q.feedback:
        raise HTTPException(409, "Feedback already submitted for this query")
    if q.status != "Resolved":
        raise HTTPException(400, "Feedback can only be given on a resolved query")
    db.add(Feedback(query_id=q.id, user_id=user.id, rating=body.rating, comments=body.comments))
    q.status = "Closed"
    db.commit()
    return serialize_query(db.get(Query, q.id), detail=True)
