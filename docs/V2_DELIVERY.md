# V2 Delivery and Verification

Completed local verification September 28, 2026. Branch:
`feature/ai-internship-platform-v2`. No push, merge or deployment was performed.

## Repository Audit

The existing FastAPI/Next.js/Supabase architecture and provider interfaces were
retained. [Detailed audit](AUDIT_V2.md) includes every provider, exact fetch paths,
live measurements, daily-volume uncertainty, baseline/current scoring algorithms,
scoring examples, student suitability, database review and prioritized follow-up.
[Pre-upgrade findings](UPGRADE_AUDIT.md) record the original risks.

## Implemented Improvements

- Removed fabricated pay/date/remote assumptions and the RemoteOK logo-as-website bug.
- Conservative URL/requisition-aware deduplication with unique source counts,
  original URLs, stable IDs and preserved application state.
- Editable candidate profiles, deterministic skill match and eligibility checks,
  explainable opportunity/trust/freshness scores and explicit unknown values.
- Lifecycle aging without deleting jobs; legacy samples hidden and labeled.
- Atomic local updates, durable run/raw diagnostics and Supabase transactional RPCs.
- Provider throttling, response caching, bounded retries, failure isolation and cooldown.
- Application status, notes, contacts, dates, favorites, hiding and extraction corrections.
- Combined filters, lightweight natural-language parsing, pagination, sorting,
  saved searches, recommendations, actual-data analytics and safe CSV/XLSX exports.

## AI and Resume Features

Optional chat-completions-compatible AI adapter accepts only validated,
source-supported skill classification with confidence/evidence and cached results.
Invalid output and unavailable providers fall back to deterministic behavior.
Numerical scores remain deterministic. Live model quality has not been verified.

PDF/text resume processing is temporary and local to the backend. Users review
extracted skills/education before adding them to the profile. This is not full
resume understanding, OCR or an LLM-based resume service.

## Backend and Database

New APIs cover internships, recommendations, profiles, applications, corrections,
saved searches, resume extraction, source health, discovery history and analytics.
Legacy jobs/discovery/export routes remain available. Supabase migration adds
intelligence fields, query indexes, run detail JSON, private state, RLS and
service-only RPCs. It preserves existing IDs and tracking records.

No live Supabase project was changed. SQL verification used the actual schema and
migration in PGlite. Hosted PostgREST/auth/network behavior remains unverified.

## Frontend

Responsive workspace with overview, discovery, saved roles, application pipeline,
insights, sources and profile pages. Job details include score breakdowns, eligibility,
trust evidence, skills, original links and tracker controls. Mobile filters use
focus containment and Escape; details use a native dialog. Loading, retry and empty
states are present. Browser tests use separate, explicitly labeled fixtures.

## Verification Results

| Check | Result |
|---|---|
| Backend pytest | **53 passed** |
| Frontend lint | Passed |
| TypeScript typecheck | Passed |
| Next.js production build | Passed; Next.js 15.5.26 |
| PostgreSQL migration | Passed twice, with legacy records preserved |
| Database RPC tracking round-trip | Passed; rediscovery preserves notes/status/favorite |
| RLS/grants | Anonymous table/RPC access denied; service-role access succeeds |
| Browser workflow | Passed on 1440px desktop and 390px mobile |
| Browser console | No errors during the successful workflow |
| Pagination, filters, saved search, profile | Passed browser and/or API checks |
| Application status/notes/favorites | Persisted across views and reloads |
| CSV/XLSX | Passed filtering and formula-injection tests |
| Password/access controls | Missing/wrong credentials denied; valid accepted |
| Host/origin controls | Hostile origin and unapproved host denied |
| Production npm audit | **0 vulnerabilities** at verification time |
| Git whitespace check | Passed |

One third-party test-client deprecation warning remains (Starlette/httpx); it is
not a test failure. No backend request failures were observed in the successful
browser run. Migration tests do not replace staging verification on real Supabase.

Live read-only probe September 27: 67 adapter-returned records, 66 accepted,
including seven program catalogs, nine with paid evidence and one remote.
Two restricted sources remained disabled. Daily job volume is **not established**.

Local screenshots from isolated browser tests:

- `frontend/test-results/desktop.png`
- `frontend/test-results/mobile.png`
- `frontend/test-results/mobile-detail.png`

## Security and Performance

Server-only tokens/AI keys; same-origin API proxy; host allowlists; private workspace
password guard for remote hosts; restricted CORS; RLS and revoked client grants;
no raw HTML injection; public-link validation; 2 MB upload/proxy limit and 10-page
PDF limit; spreadsheet formula neutralization; no anti-bot bypass.

Pagination reduces response size, caching reduces repeated provider/model requests,
and concurrency limits bound collection. Full-collection scoring and linear merge
candidate searches remain scalability limits. This is a tested single-owner core,
not a completed multi-user production deployment.

## Important Remaining Work

1. Before public multi-user use: real account/tenant ownership, resource-isolated PDF
   parsing, TLS/gateway controls and deployment-specific security testing.
2. Better current internship coverage and at least seven days of unique/day telemetry.
3. Indexed database filtering and profile-versioned score materialization at scale.
4. Richer location/degree/work-authorization and required/preferred skill evidence.
5. Labeled scoring/trust evaluation; no probability or hiring-outcome claims yet.
6. Distributed discovery locks/backoff and operator-approved Supabase history retention.

Stored reminder dates do not notify. Semantic embeddings, command palette, alerts
and auto-apply were intentionally not added.

## Files and Git

Main changes: `backend/app/`, `backend/tests/`, `backend/scripts/`,
`frontend/components/`, frontend routes/proxy/access guard, migration, environment
example, README and audit/verification documents. Private data and secrets are ignored.

Milestone commits:

- `73b8231` - explainable intelligence, safe discovery, API tests and migration.
- `15a7c5f` - responsive discovery/tracking workspace, access guard and browser checks.
- Final documentation commit follows these milestones; see Git history for its ID.

## Run and Configure

Normal local preview: http://127.0.0.1:3000 with backend on http://127.0.0.1:8000.
The test servers and their temporary fixture database were stopped after verification.

See [README](../README.md) for exact setup/start/test commands and [.env.example](../.env.example)
for configuration. No new secret is required for local deterministic mode. AI is
disabled unless explicitly configured. Supabase migration is a separate backed-up
operator action. A remote workspace requires a password, matching server API token,
allowed hosts and HTTPS. Existing local records are not automatically synchronized
to Supabase.
