# Intelligent College FAQ Chatbot and Query Management System

Full-stack project matching the course report: **React + Vite** frontend, **FastAPI** backend,
**PostgreSQL** (SQLite in dev), **LangChain + FAISS** RAG chatbot, **JWT + bcrypt** auth with server-side
role checks, **Docker**, **Kubernetes** manifests and a **GitHub Actions** CI workflow.

## Quick start (no Docker, no API key)

```bash
# 1. Backend (http://localhost:8000, API docs at /docs)
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload

# 2. Frontend (http://localhost:5173) in a second terminal
cd frontend
npm install
npm run dev
```

On first start the backend creates the tables, seeds departments, demo users and sample FAQs, and builds the
FAISS index. With no `DATABASE_URL` it uses a local SQLite file, so you can start immediately.

| Role | Email | Password |
|---|---|---|
| Administrator | admin@college.edu | Admin@123 |
| Staff (one per department) | staff.accounts@college.edu, staff.hostel@college.edu, staff.admissions@college.edu, staff.examination@college.edu, staff.academics@college.edu, staff.administration@college.edu | Staff@123 |
| Student | student@college.edu | Student@123 |

Set `SEED_DEMO=false` in production and change `ADMIN_EMAIL` / `ADMIN_PASSWORD` / `JWT_SECRET`.
`python -m app.seed` is the setup script that creates the administrator (the admin role cannot be chosen at registration).

## Docker and Kubernetes

```bash
docker compose up --build            # app at http://localhost:3000, API at :8000
# Kubernetes (Minikube)
docker build -t college-faq-backend:latest ./backend
docker build -t college-faq-frontend:latest ./frontend
minikube image load college-faq-backend:latest college-faq-frontend:latest
kubectl apply -f k8s/ && kubectl get pods && minikube service college-faq-frontend-svc
```

## How the chatbot works

1. FAQ entries (and uploaded `.txt/.md/.pdf` documents) are chunked, embedded and stored in FAISS (`app/rag.py`).
2. A question is embedded, the top 4 chunks are retrieved and the best cosine score is the **confidence**.
3. Below `CONFIDENCE_THRESHOLD` the LLM is not called: the user gets a fallback and a **Raise a query** button
   that pre-fills the form and links the ticket to the chat log.
4. Otherwise the answer is shown with its **sources**. Every exchange is stored in `chat_logs`.

**Offline by default:** with no key, embeddings are local hashed vectors and the answer is the best matching FAQ answer.
For fluent, grounded LLM answers set in `.env`: `LLM_API_KEY=sk-...`, `EMBEDDING_PROVIDER=openai`, `CONFIDENCE_THRESHOLD=0.45`,
then re-index from **Knowledge base → Re-index**. Tune the threshold on your own question set (report Section 5.4).

## Features by role

- **Student:** chatbot, raise query (category, priority, attachment), track status and replies, feedback (1–5) that closes the query, in-app notifications.
- **Staff:** department inbox, reply, mark In Progress / Resolved, suggest FAQ entries, department analytics and the two department reports.
- **Admin:** all queries, assign/escalate, users and departments, FAQ and document management with atomic re-index, analytics, all four reports with PDF/Excel export.
- **Workflow:** Open → Assigned → In Progress → Resolved → Closed (enforced server-side; Resolved queries auto-close after `AUTO_CLOSE_DAYS`).

## Tests

```bash
cd backend && pytest        # 14 tests covering report cases TC-02…TC-27 (auth, RBAC, workflow, chatbot, reports)
```

## Before you submit

- The seeded FAQs are **sample data**; replace them with real college information.
- Take the screenshots for Chapter 4/6 from the running app and fill the highlighted fields in the report
  (repo URL, hosting URLs, embedding/LLM names, chatbot evaluation counts).
- If you don’t configure CI/CD or Kubernetes for real, say so in Chapter 6 as the report template instructs.
- Report Section 2.9: staff do not use the chatbot, so the chat API is student-only. Staff get the Query and Department reports; the Chatbot and Unanswered reports are admin-only.
