from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from ..common import serialize_user
from ..database import get_db
from ..models import User
from ..security import create_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=160)
    password: str = Field(min_length=8, max_length=128)
    role: str = "student"

    @field_validator("email")
    @classmethod
    def valid_email(cls, v):
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Enter a valid email address")
        return v


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    # Role whitelist: administrators are never created through public registration (TC-22).
    if body.role not in ("student", "staff"):
        raise HTTPException(400, "This role cannot be registered publicly")
    if body.role == "staff":
        raise HTTPException(400, "Staff accounts are created by the administrator")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(409, "Already registered with this email")
    user = User(full_name=body.full_name.strip(), email=body.email, password_hash=hash_password(body.password),
                role="student")
    db.add(user)
    db.commit()
    return {"access_token": create_token(user), "token_type": "bearer", "user": serialize_user(user)}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.strip().lower()).first()
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return {"access_token": create_token(user), "token_type": "bearer", "user": serialize_user(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return serialize_user(user)
