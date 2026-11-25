import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from .. import rag
from ..common import iso
from ..config import CATEGORIES, settings
from ..database import get_db
from ..models import FAQEntry, KBDocument, Query, User
from ..security import role_required

router = APIRouter(prefix="/api", tags=["knowledge-base"])


class FAQIn(BaseModel):
    category: str
    question: str = Field(min_length=5)
    answer: str = Field(min_length=3)
    source_doc: str | None = None
    is_active: bool = True
    status: str | None = None


def _faq(f: FAQEntry):
    return {"id": f.id, "category": f.category, "question": f.question, "answer": f.answer,
            "source_doc": f.source_doc, "is_active": f.is_active, "status": f.status,
            "suggested_by": f.suggested_by, "updated_at": iso(f.updated_at)}


@router.get("/faqs")
def list_faqs(user: User = Depends(role_required("admin", "staff")), db: Session = Depends(get_db)):
    qs = db.query(FAQEntry)
    if user.role == "staff":  # staff see approved entries and their own suggestions
        qs = qs.filter((FAQEntry.status == "approved") | (FAQEntry.suggested_by == user.id))
    return [_faq(f) for f in qs.order_by(FAQEntry.id.desc()).all()]


@router.post("/faqs", status_code=201)
def add_faq(body: FAQIn, user: User = Depends(role_required("admin", "staff")), db: Session = Depends(get_db)):
    if body.category not in CATEGORIES:
        raise HTTPException(400, "Unknown category")
    admin = user.role == "admin"
    f = FAQEntry(category=body.category, question=body.question.strip(), answer=body.answer.strip(),
                 source_doc=body.source_doc, is_active=admin and body.is_active,
                 status="approved" if admin else "pending", suggested_by=None if admin else user.id)
    db.add(f)
    db.commit()
    return _faq(f)


@router.put("/faqs/{faq_id}")
def edit_faq(faq_id: int, body: FAQIn, user: User = Depends(role_required("admin")), db: Session = Depends(get_db)):
    f = db.get(FAQEntry, faq_id)
    if not f:
        raise HTTPException(404, "FAQ not found")
    f.category, f.question, f.answer = body.category, body.question.strip(), body.answer.strip()
    f.source_doc, f.is_active = body.source_doc, body.is_active
    if body.status in ("approved", "pending"):
        f.status = body.status
    db.commit()
    return _faq(f)


@router.delete("/faqs/{faq_id}", status_code=204)
def delete_faq(faq_id: int, user: User = Depends(role_required("admin")), db: Session = Depends(get_db)):
    f = db.get(FAQEntry, faq_id)
    if not f:
        raise HTTPException(404, "FAQ not found")
    db.delete(f)
    db.commit()


# ---------- documents ----------
def _read_document(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    return path.read_text(encoding="utf-8", errors="ignore")


@router.get("/kb/documents")
def list_documents(user: User = Depends(role_required("admin")), db: Session = Depends(get_db)):
    return [{"id": d.id, "filename": d.filename, "is_active": d.is_active, "uploaded_at": iso(d.uploaded_at)}
            for d in db.query(KBDocument).order_by(KBDocument.id.desc())]


@router.post("/kb/upload", status_code=201)
async def upload_document(file: UploadFile = File(...), user: User = Depends(role_required("admin")),
                          db: Session = Depends(get_db)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".txt", ".md", ".pdf"):
        raise HTTPException(400, "Only .txt, .md and .pdf documents are supported")
    data = await file.read()
    if not data:
        raise HTTPException(400, "The file is empty")
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(400, "File is larger than 10 MB")
    stored = f"{uuid.uuid4().hex}{ext}"
    (settings.DOC_DIR / stored).write_bytes(data)
    if not _read_document(settings.DOC_DIR / stored).strip():
        (settings.DOC_DIR / stored).unlink(missing_ok=True)
        raise HTTPException(400, "No readable text found in this document")
    d = KBDocument(filename=Path(file.filename).name[:200], path=stored)
    db.add(d)
    db.commit()
    return {"id": d.id, "filename": d.filename, "is_active": d.is_active}


@router.patch("/kb/documents/{doc_id}")
def toggle_document(doc_id: int, user: User = Depends(role_required("admin")), db: Session = Depends(get_db)):
    d = db.get(KBDocument, doc_id)
    if not d:
        raise HTTPException(404, "Document not found")
    d.is_active = not d.is_active
    db.commit()
    return {"id": d.id, "is_active": d.is_active}


@router.delete("/kb/documents/{doc_id}", status_code=204)
def delete_document(doc_id: int, user: User = Depends(role_required("admin")), db: Session = Depends(get_db)):
    d = db.get(KBDocument, doc_id)
    if not d:
        raise HTTPException(404, "Document not found")
    (settings.DOC_DIR / d.path).unlink(missing_ok=True)
    db.delete(d)
    db.commit()


def reindex(db: Session) -> dict:
    docs = [Document(page_content=f"Q: {f.question}\nA: {f.answer}",
                     metadata={"source": f.source_doc or f"FAQ: {f.category}"})
            for f in db.query(FAQEntry).filter(FAQEntry.is_active.is_(True), FAQEntry.status == "approved")]
    n_faq = len(docs)
        for d in db.query(KBDocument).filter(KBDocument.is_active.is_(True)):
            path = settings.DOC_DIR / d.path
            if not path.exists():
            continue
    text = _read_document(path)
        if text.strip():
            docs.append(Document(page_content=text, metadata={"source": d.filename}))
    return {"faq_entries": n_faq, "documents": len(docs) - n_faq, "chunks": rag.build_index(docs)}


@router.post("/kb/reindex")
def reindex_route(user: User = Depends(role_required("admin")), db: Session = Depends(get_db)):
    try:
        return reindex(db)
    except Exception as exc:  # previous index stays in place on failure (UC-05)
        raise HTTPException(500, f"Re-indexing failed; the previous index is still active ({exc})")
