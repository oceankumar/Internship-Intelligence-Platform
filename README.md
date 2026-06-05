# Internship Intelligence Platform

Phase 1 builds an internship discovery and management system for a CS and AI student seeking paid frontend, full-stack, React, Next.js, startup, and reasonable AI internships.

This phase intentionally does not include auto-apply, browser submission automation, or resume editing.

## Architecture

- `backend/`: FastAPI discovery API, provider modules, normalization, scoring, trust checks, CSV and Excel exports.
- `frontend/`: Next.js dashboard for reviewing opportunities, trust flags, scores, and exports.
- `supabase/schema.sql`: Production-ready Postgres schema for Supabase.

## Local Setup

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
cp ../.env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Supabase

1. Create a Supabase project.
2. Run `supabase/schema.sql` in the SQL editor or through migrations.
3. Set these environment variables for the backend:

```bash
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
```

If Supabase variables are not present, the backend falls back to a local JSON repository at `backend/data/internships.json`.

## Discovery Sources

Current provider modules:

- RemoteOK
- Y Combinator Jobs
- Work at a Startup
- Wellfound

Each source implements the same provider contract, so future LinkedIn, Internshala, Indeed, and company-career-page connectors can be added without changing the rest of the pipeline.

## API

- `GET /health`
- `GET /api/jobs`
- `POST /api/discovery/run`
- `GET /api/companies/suspicious`
- `GET /api/export.csv`
- `GET /api/export.xlsx`

## Product Rules

Relevance favors:

- Paid roles
- Remote or India-friendly roles
- Frontend, React, Next.js, web, full-stack, startup engineering, and product engineering internships
- Reasonable requirements for a student with about 3 months of internship experience

Trust scoring flags companies with weak signals such as missing website, thin descriptions, missing LinkedIn presence, no product evidence, and vague or unpaid listings.

