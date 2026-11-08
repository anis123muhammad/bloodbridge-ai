# BloodBridge AI

An Agentic AI-Powered Blood Donation Matching and Emergency Coordination Platform.

Built for the **Vultr Agent Rush Hackathon**.

---

## Monorepo Architecture

- **`backend/`**: FastAPI + PostgreSQL backend featuring 6 AI agents, state-machine orchestration, transparent priority scoring, Alembic migrations, and synthetic demo datasets.
- **`app/`**: Next.js 16 (App Router) + Tailwind CSS v4 frontend with dedicated portals for:
  - Hospital Coordination (`/hospital`)
  - Donor Dashboard (`/donor`)
  - Administrator Overview & Audit Log Viewer (`/admin`)
  - Authentication & Role Routing (`/login`, `/register`)

---

## Quick Start

### 1. Backend Setup (FastAPI)

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Run migrations and start API
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000
```

- API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Endpoint: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 2. Frontend Setup (Next.js)

```bash
npm install
npm run dev
```

- Web Application: [http://localhost:3000](http://localhost:3000)
- Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `.env.local` to connect to the backend.

---

## Safety & Hackathon Prototype Disclaimer

This system operates on **synthetic demo data only**. No real medical triage, real emergency dispatches, or unsolicited communications are performed. All donor contact actions require explicit human-in-the-loop staff approval.
