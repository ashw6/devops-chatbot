from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .. import rag
from ..common import iso
from ..database import get_db
from ..models import ChatLog, User
from ..security import role_required

router = APIRouter(prefix="/api/chat", tags=["chatbot"])


class AskIn(BaseModel):
    question: str


@router.post("/ask")
def ask(body: AskIn, user: User = Depends(role_required("student")), db: Session = Depends(get_db)):
    question = body.question.strip()
    if not question:
        return {"answer": "", "sources": [], "escalate": False, "confidence": 0.0, "log_id": None}
    result = rag.answer(question[:1000])
    log = ChatLog(user_id=user.id, user_question=question, bot_answer=result["answer"],
                  sources="|".join(result["sources"]), confidence=result["confidence"],
                  escalated=result["escalate"])
    db.add(log)
    db.commit()
    return {**result, "log_id": log.id}


@router.get("/history")
def history(limit: int = 50, user: User = Depends(role_required("student")), db: Session = Depends(get_db)):
    logs = (db.query(ChatLog).filter(ChatLog.user_id == user.id)
            .order_by(ChatLog.id.desc()).limit(min(limit, 200)).all())
    return [{"id": l.id, "question": l.user_question, "answer": l.bot_answer,
             "sources": [s for s in (l.sources or "").split("|") if s], "confidence": l.confidence,
             "escalate": l.escalated, "created_at": iso(l.created_at)} for l in reversed(logs)]
