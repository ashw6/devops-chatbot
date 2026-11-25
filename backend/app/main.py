import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from . import rag
from .config import settings
from .database import Base, SessionLocal, engine
from .models import Query, now
from .routers import admin, auth, chat, dashboard, kb, queries, reports
from .seed import seed


def auto_close_resolved(db):
    """Resolved queries with no feedback are closed after AUTO_CLOSE_DAYS (FR-10)."""
    cutoff = now() - timedelta(days=settings.AUTO_CLOSE_DAYS)
    n = db.query(Query).filter(Query.status == "Resolved", Query.resolved_at < cutoff) \
        .update({"status": "Closed"})
    db.commit()
    return n


async def _closer():
    while True:
        await asyncio.sleep(3600)
        with SessionLocal() as db:
            auto_close_resolved(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
        if rag.get_store() is None:
            kb.reindex(db)
        auto_close_resolved(db)
    task = asyncio.create_task(_closer())
    yield
    task.cancel()


app = FastAPI(title="Intelligent College FAQ Chatbot and Query Management System", version="1.0.0",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    msgs = []
    for e in exc.errors():
        field = ".".join(str(p) for p in e["loc"] if p not in ("body", "query", "form"))
        msgs.append(f"{field}: {e['msg']}" if field else e["msg"])
    return JSONResponse(status_code=400, content={"detail": "; ".join(msgs)})


for module in (auth, chat, queries, admin, kb, reports, dashboard):
    app.include_router(module.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
