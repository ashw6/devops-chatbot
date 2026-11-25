import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent


def _path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else BASE_DIR / p


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'data' / 'app.db'}"
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]
    VECTOR_STORE_PATH = _path(os.getenv("VECTOR_STORE_PATH", "data/faiss_index"))
    UPLOAD_DIR = _path(os.getenv("UPLOAD_DIR", "data/uploads"))
    DOC_DIR = _path(os.getenv("DOC_DIR", "data/docs"))
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.30"))
    SEED_DEMO = os.getenv("SEED_DEMO", "true").lower() == "true"
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@college.edu")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123")
    AUTO_CLOSE_DAYS = int(os.getenv("AUTO_CLOSE_DAYS", "7"))
    MAX_UPLOAD_MB = 5


settings = Settings()
for d in (settings.UPLOAD_DIR, settings.DOC_DIR, BASE_DIR / "data"):
    d.mkdir(parents=True, exist_ok=True)

ROLES = ("student", "staff", "admin")
STATUSES = ("Open", "Assigned", "In Progress", "Resolved", "Closed")
PRIORITIES = ("Low", "Normal", "High")
# Category -> department routing table (Section 3.8 / 4.7.4 of the report)
CATEGORY_DEPARTMENT = {
    "Admissions": "Admissions",
    "Fees": "Accounts",
    "Scholarship": "Accounts",
    "Examination": "Examination",
    "Academics": "Academics",
    "Hostel": "Hostel",
    "Certificates": "Administration",
    "Other": "Administration",
}
CATEGORIES = tuple(CATEGORY_DEPARTMENT)
# State machine (Section 3.6)
TRANSITIONS = {
    "Open": {"Assigned", "In Progress"},
    "Assigned": {"In Progress", "Open"},
    "In Progress": {"Resolved"},
    "Resolved": {"Closed", "In Progress"},
    "Closed": set(),
}
