import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["VECTOR_STORE_PATH"] = f"{_tmp}/faiss"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["DOC_DIR"] = f"{_tmp}/docs"
os.environ["LLM_API_KEY"] = ""
os.environ["SEED_DEMO"] = "true"

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def student(client):
    return login(client, "student@college.edu", "Student@123")


@pytest.fixture(scope="session")
def admin(client):
    return login(client, "admin@college.edu", "Admin@123")


@pytest.fixture(scope="session")
def accounts_staff(client):
    return login(client, "staff.accounts@college.edu", "Staff@123")


@pytest.fixture(scope="session")
def hostel_staff(client):
    return login(client, "staff.hostel@college.edu", "Staff@123")
