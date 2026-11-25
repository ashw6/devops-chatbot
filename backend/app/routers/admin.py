from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..common import notify, serialize_user, serialize_query, ticket
from ..config import ROLES
from ..database import get_db
from ..models import Department, Query, User
from ..security import get_current_user, hash_password, role_required

router = APIRouter(prefix="/api", tags=["admin"])


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=8, max_length=128)
    role: str
    department_id: int | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    department_id: int | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)


class DeptIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    head_user_id: int | None = None


class AssignIn(BaseModel):
    assigned_to: int
    department_id: int | None = None


@router.get("/meta")
def meta(user: User = Depends(get_current_user)):
    from ..config import CATEGORIES, PRIORITIES, STATUSES, TRANSITIONS
    return {"categories": CATEGORIES, "priorities": PRIORITIES, "statuses": STATUSES,
            "transitions": {k: sorted(v) for k, v in TRANSITIONS.items()}}


@router.get("/departments")
def list_departments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [{"id": d.id, "name": d.name, "head_user_id": d.head_user_id}
            for d in db.query(Department).order_by(Department.name)]


@router.post("/admin/departments", status_code=201)
def create_department(body: DeptIn, user: User = Depends(role_required("admin")), db: Session = Depends(get_db)):
    if db.query(Department).filter(Department.name == body.name.strip()).first():
        raise HTTPException(409, "Department already exists")
    d = Department(name=body.name.strip(), head_user_id=body.head_user_id)
    db.add(d)
    db.commit()
    return {"id": d.id, "name": d.name, "head_user_id": d.head_user_id}


@router.put("/admin/departments/{dept_id}")
def update_department(dept_id: int, body: DeptIn, user: User = Depends(role_required("admin")),
                      db: Session = Depends(get_db)):
    d = db.get(Department, dept_id)
    if not d:
        raise HTTPException(404, "Department not found")
    d.name, d.head_user_id = body.name.strip(), body.head_user_id
    db.commit()
    return {"id": d.id, "name": d.name, "head_user_id": d.head_user_id}


@router.get("/admin/users")
def list_users(role: str | None = None, department_id: int | None = None,
               user: User = Depends(role_required("admin")), db: Session = Depends(get_db)):
    qs = db.query(User)
    if role:
        qs = qs.filter(User.role == role)
    if department_id:
        qs = qs.filter(User.department_id == department_id)
    return [serialize_user(u) for u in qs.order_by(User.role, User.full_name).all()]


@router.post("/admin/users", status_code=201)
def create_user(body: UserCreate, user: User = Depends(role_required("admin")), db: Session = Depends(get_db)):
    if body.role not in ROLES:
        raise HTTPException(400, "Unknown role")
    if body.role == "staff" and not body.department_id:
        raise HTTPException(400, "Staff users need a department")
    email = body.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Already registered with this email")
    u = User(full_name=body.full_name.strip(), email=email, password_hash=hash_password(body.password),
             role=body.role, department_id=body.department_id if body.role == "staff" else None)
    db.add(u)
    db.commit()
    return serialize_user(u)


@router.patch("/admin/users/{user_id}")
def update_user(user_id: int, body: UserUpdate, admin: User = Depends(role_required("admin")),
                db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == admin.id and (body.is_active is False or (body.role and body.role != "admin")):
        raise HTTPException(400, "You cannot deactivate or demote your own account")
    if body.role is not None:
        if body.role not in ROLES:
            raise HTTPException(400, "Unknown role")
        u.role = body.role
    if body.full_name:
        u.full_name = body.full_name.strip()
    if body.department_id is not None:
        u.department_id = body.department_id or None
    if body.is_active is not None:
        u.is_active = body.is_active
    if body.password:
        u.password_hash = hash_password(body.password)
    db.commit()
    return serialize_user(u)


@router.patch("/admin/queries/{query_id}/assign")
def assign_query(query_id: int, body: AssignIn, admin: User = Depends(role_required("admin")),
                 db: Session = Depends(get_db)):
    q = db.get(Query, query_id)
    if not q:
        raise HTTPException(404, "Query not found")
    if q.status == "Closed":
        raise HTTPException(409, "This query is closed and can no longer be changed")
    staff = db.get(User, body.assigned_to)
    if not staff or staff.role != "staff" or not staff.is_active:
        raise HTTPException(400, "Choose an active staff member")
    q.assigned_to = staff.id
    q.department_id = body.department_id or staff.department_id or q.department_id
    if q.status == "Open":
        q.status = "Assigned"
    notify(db, staff.id, f"{ticket(q)} was assigned to you: {q.subject}", q.id)
    notify(db, q.student_id, f"{ticket(q)} was assigned to {staff.full_name}", q.id)
    db.commit()
    return serialize_query(q, detail=True)
