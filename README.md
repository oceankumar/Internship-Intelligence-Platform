# Internship Intelligence Platform

A private, single-owner workspace for discovering internships, understanding fit,
and tracking applications. Next.js/React, FastAPI/Pydantic, and local JSON or
Supabase PostgreSQL. No auto-apply, invented salary, or required AI subscription.

## Features

- Public-source discovery with source health, raw records and run diagnostics.
- Editable candidate profile and explainable match, eligibility, trust and opportunity scores.
- Optional validated AI classification with evidence, confidence checks and cache.
- Combined filters, pagination, sorting, saved searches and shortlists.
- Application status, notes, contacts, interview/reminder dates and corrections.
- Overview, discovery, saved roles, applications, insights, sources and profile views.
- Temporary PDF/text resume extraction with review before adding skills.
- CSV/Excel exports using the same filters and formula-injection protection.

See [the complete audit](docs/AUDIT_V2.md) for measured provider behavior,
formulas, database review and prioritized follow-up.
[Baseline findings](docs/UPGRADE_AUDIT.md) describe the pre-upgrade implementation.
Other older status documents and screenshots describe historical releases.

## Architecture

```mermaid
flowchart LR
  Sources[Public feeds and boards] --> Providers[Throttled provider adapters]
  Providers --> Parse[Normalize and preserve evidence]
  Parse --> Rules[Internship and trust checks]
  Rules --> AI[Optional validated classification]
  AI --> Score[Profile match and eligibility]
  Score --> Merge[Conservative dedupe]
  Merge --> Store[Local JSON or Supabase]
  Store --> API[FastAPI filtering and ranking]
  API --> Proxy[Private Next.js API proxy]
  Proxy --> UI[Discovery and tracking workspace]
  Profile[Candidate profile] --> Score
  Providers --> Runs[Run diagnostics and raw records]
```

Scores are recalculated on reads to reflect current profile and freshness. This
keeps the small-workspace experience consistent but is not yet large-scale SQL
ranking. Missing metadata stays unknown. Source health means fetch health,
not verified employer legitimacy.

## Local Setup

Tested with Python 3.14 and Node 24. Use Python 3.11+ and Node 22+.
Keep both servers bound to loopback. No credentials are needed locally.

Backend, from the repository root:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend, in a second terminal:

```sh
cd frontend
npm ci
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open http://127.0.0.1:3000. Start with My profile, then Discover new roles.
A new store is empty: no demo data is inserted. Existing jobs and IDs are preserved.
Known historical sample IDs are hidden and labeled; provider-invented generic
stipends are no longer pay evidence. Reading does not delete or rewrite the store.

Backend config loads backend/.env when started from backend/. Data paths resolve
relative to the backend directory. Local diagnostics live beside the store in
internships.state.json; both files are private.

## Configuration

Backend variables are documented in [.env.example](.env.example).

| Variable | Default / purpose |
|---|---|
| APP_ENV | local; nonlocal requires API token |
| FRONTEND_ORIGIN | http://localhost:3000 |
| API_TOKEN | Empty only for loopback local mode; strong secret remotely |
| ALLOWED_HOSTS | Backend JSON array, default localhost/127.0.0.1/testserver |
| LOCAL_DATA_PATH | data/internships.json |
| SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY | Both enable Supabase |
| REQUEST_TIMEOUT_SECONDS | 20 |
| PROVIDER_CONCURRENCY, PROVIDER_REQUEST_INTERVAL | 2 providers, 1 second per host |
| PROVIDER_CACHE_SECONDS, DISCOVERY_COOLDOWN_SECONDS | 3600 / 60 |
| GREENHOUSE_BOARDS | JSON list: stripe, reddit, gitlab, anthropic, figma, vercel |
| STALE_DAYS, INACTIVE_DAYS, MINIMUM_TRUST | 30 / 90 / 40 |
| BLOCKED_COMPANIES, BLOCKED_DOMAINS | Operator-controlled JSON lists |
| ENABLE_AI_CLASSIFICATION | false |
| AI_BASE_URL, AI_MODEL, AI_API_KEY | Chat-completions endpoint/model/key |
| AI_CONFIDENCE_THRESHOLD, AI_CACHE_SECONDS | 0.8 / 604800 |
| RESUME_MAX_BYTES | 2000000; proxy also enforces 2 MB |

Frontend server-only variables belong in frontend/.env.local:

```dotenv
API_BASE_URL=http://127.0.0.1:8000
API_TOKEN=
ALLOWED_HOSTS=localhost:3000,127.0.0.1:3000
```

Never use NEXT_PUBLIC_ for secrets. The old NEXT_PUBLIC_API_BASE_URL is unused.
Frontend ALLOWED_HOSTS is comma-separated with ports; the backend's identically
named variable is a JSON list without ports. Keep their environment files separate.

For remote single-owner use: set WORKSPACE_USER (default owner), a strong
WORKSPACE_PASSWORD, the actual allowed frontend host, and matching backend/proxy
API_TOKEN. Use HTTPS and keep the backend private. Remote hosts fail closed without
a workspace password. Checks run in middleware and again in the API proxy.
This is not multi-user authentication.

## Supabase

Back up the database first. For a new database, apply supabase/schema.sql, then
supabase/migrations/202609260001_intelligence_v2.sql. Existing installations using
the current base schema need only the migration. Older custom schemas need staging
compatibility review. No live migration runs automatically at startup.

The migration keeps IDs/data, adds intelligence fields/indexes, enables RLS,
restricts public tables to server credentials, and creates transactional
upsert/tracking RPCs. It deliberately does not allow unrestricted direct browser
table access. Service-role keys belong only in the backend.

Local JSON and Supabase are alternative modes, not automatic synchronization.
Setting credentials does not upload local records. Plan an explicit backed-up import.

## Providers

Six enabled adapters: RemoteOK public JSON; YC public structured listings/JSON-LD;
SimplifyJobs and GitHub community trackers; configured Greenhouse boards; and an
explicitly labeled program catalog. Work at a Startup and Wellfound remain disabled.
No protection bypass or authenticated scraping is attempted.

The September 27 capped probe accepted 66 records, including seven program-catalog
entries with unverified opening windows. This is not daily volume. See the audit
for exact URLs, counts and failure points. Tracker paths are season-specific.

## API

Except /health, routes require a token or loopback access in local mode.

| Endpoint | Behavior |
|---|---|
| GET /api/internships | Page, limit 1-100, sort and combined filters |
| GET /api/internships/{id} | Details and evidence |
| GET /api/recommendations | Up to 12 strong/apply-now matches |
| GET /api/jobs | Compatibility full-list endpoint |
| POST /api/discovery/run | Sources, query, limit_per_source, persist |
| GET /api/discovery/runs and /{id} | Recent runs or one run |
| GET /api/providers/health | Latest outcome and success/failure timestamps |
| GET/PUT /api/profile | Single-owner profile |
| GET /api/applications | Tracked/favorited jobs |
| PATCH /api/applications/{id} | Status, notes, favorites, hidden, dates, contact |
| PATCH /api/internships/{id}/corrections | Extraction overlay |
| GET/POST /api/searches; DELETE /api/searches/{name} | Saved searches |
| GET /api/analytics/market and /api/analytics/skills | Collection statistics |
| POST /api/resume/analyze | Raw PDF or UTF-8 text body; no file storage |
| GET /api/export.csv and /api/export.xlsx | Filtered exports |

Filters: q, role, skill (comma-separated), remote, country, company, paid, source,
status, favorite, min_match, min_trust, min_opportunity, posted_days, closing_days,
max_experience, min_stipend, currency, period, include_hidden, include_inactive,
applications and recommended. Stipend comparisons require currency and pay period.
No guessed conversion rates.

Read-only discovery:

```sh
curl http://127.0.0.1:8000/api/discovery/run \
  -H 'Content-Type: application/json' \
  -d '{"sources":["startup_career_pages"],"limit_per_source":20,"persist":false}'
```

persist=false skips run/raw/job/AI-cache writes. Discovery is manual, not scheduled.
Reminder dates are stored but do not send notifications.

## AI and Privacy

Core behavior works without a model. When enabled, only public job title/description
are sent to the configured model, not candidate profiles or resumes. Pydantic rejects
invalid output; confidence and verbatim evidence are checked. Numerical ranking
remains deterministic. Only source-supported skill classifications currently change
ranking inputs; other proposals remain in provenance. No separate paid fallback.

Resume extraction recognizes skills and education lines, not reliable experience
or project timelines. Scanned PDFs need external OCR. Encrypted or more-than-10-page
PDFs are rejected. Public uploads require resource-isolated PDF parsing before launch.

## Verification

```sh
cd backend
.venv/bin/python -m pytest -q
PYTHONPATH=. .venv/bin/python scripts/probe_providers.py
```

The second command makes bounded live read-only requests. It does not measure daily
supply. Provider unit tests use fixtures and make no network requests.

```sh
cd frontend
npm run lint
npm run typecheck
npm run build
node scripts/test-migration.mjs
```

The migration test uses PGlite's PostgreSQL engine, not a live Supabase instance.
For browser tests, run these in separate terminals:

```sh
# From backend/
PYTHONPATH=. .venv/bin/python scripts/serve_test_workspace.py
# From frontend/, after npm run build
API_BASE_URL=http://127.0.0.1:8011 ALLOWED_HOSTS=127.0.0.1:3011,localhost:3011 \
  npm run start -- --hostname 127.0.0.1 --port 3011
# From frontend/
npx playwright install chromium
node scripts/browser-check.mjs
```

Fixtures are labeled and stored temporarily. Screenshots go to ignored
frontend/test-results/. The script refuses to reset non-fixture data.

## Known Limits

- No verified daily throughput or source-completeness guarantee.
- Program catalogs are not verified openings; unknown compensation is common.
- Single-owner profile/tracking; no tenant authentication or ownership.
- Full-collection ranking and O(N*M) merging need indexed SQL at larger scale.
- Distributed locks/backoff and automatic Supabase history retention are absent.
- Eligibility vocabulary, geography, skill semantics and trust need labeled evaluation.
- No live LLM or hosted Supabase verification without credentials.
- Optional alerts, command palette, embeddings and auto-apply are absent.

## Project Map

- backend/app/providers: source adapters.
- backend/app/pipeline: parsing, dedupe, trust, eligibility, lifecycle and scoring.
- backend/app/services: repositories, AI, filters and exports.
- backend/tests: unit/API/provider regression coverage.
- frontend/app: routes, private API proxy, layout and styles.
- frontend/components: workspace views and reusable controls.
- frontend/scripts: database/browser verification.
- supabase: base schema and non-destructive migration.
- docs/AUDIT_V2.md: detailed current audit.

Created by Ocean Kumar.
