# InternAI Current Status

Verification date: October 5, 2026 (Asia/Kolkata). This is the current release document; historical audits describe earlier stages.

- Baseline main: `687b3c7`, PR #1 already merged. Final release work is on `release/resume-ready-v1`; no duplicate V3 merge.
- Backend: **112 tests passed**, expanded from a reproduced 95-test baseline. One Starlette/httpx deprecation warning.
- Frontend: clean npm install, lint, typecheck and production build passed. Node middleware is compatible with Vercel Services.
- Migration: repeat V2/V3 schema/RLS/RPC tests passed locally in PGlite; no hosted database certification.
- Browser: private fixture discovery/tracking/reload/export and read-only demo passed at 1440px desktop / 390px mobile. Demo checks cover eight routes, search, details, disabled controls, blocked mutation requests, API readiness and screenshots without recorded runtime/API errors.
- Public source snapshot: October 5 IST (2026-10-04T19:44:00Z), 68 returned, 67 accepted including seven catalogs, 66 unique / 59 active-looking leads, 15 pay evidence, two remote, one explicitly India-compatible, zero quarantined, zero provider failures. RemoteOK yielded zero accepted internships; public YC coverage was degraded; trackers supplied thin leads. Counts are not daily volume.
- Demo: immutable sanitized real public records and generic profile. Private resume/profile/notes/contact/tracking data are not loaded. Both API layers reject writes; adapter rejects direct writes.
- Preview: Next.js + private FastAPI built successfully. After explicit approval of public read-only previews, anonymous desktop/mobile checks passed across eight routes, search, paid filters, sorting, details, exports, readiness and blocked mutations, with no recorded browser/API errors. Initial build failed on Edge middleware and was repaired, not hidden.
- Production URL: https://internai-xi.vercel.app. Anonymous desktop/mobile smoke passed for eight routes, search, paid filters, sorting, detail explanations, exports, readiness and blocked mutations. Strict host validation does not accept the secondary long project alias; use this verified primary URL.
- Supabase: **Not verified; credentials unavailable for InternAI**. ContextIQ's separate hosted database was not reused. Writable production requires Supabase; no ephemeral JSON fallback.
- AI: optional validated integration implemented and fixture tested; production model not configured. Numerical ranking remains deterministic.
- Daily cron: **Not installed** for immutable snapshot demo. Durable persistence is required first. Lease-protected discovery CLI remains available; daily yield unknown.
- Security: no secret references or test tokens found in built browser assets. Production npm audit: zero advisories; full audit: five development-only lint dependency findings. Uploaded snapshot contains no personal tracking/notes/contact data.
- Main release CI: [37231603227](https://github.com/oceankumar/Internship-Intelligence-Platform/actions/runs/37231603227) passed for `4e12b82d469ca02a9a14d1ebe4e09c9706b3b16e`. Production deployment `dpl_7VCFerUtRcknEEqsqoTv2PmffvbG` built Next.js and Python 3.12 Services from clean main and passed public smoke. GitHub integration is connected with main as production branch. The final documentation commit is rechecked and redeployed; exact final main SHA is in the release handoff/tag because a source document cannot embed its own hash.
- Production runtime error query after smoke returned no entries. Deployment metadata confirmed the main GitHub commit SHA; anonymous proxy readiness reported `public_snapshot` and `ai_configured=false`.

## Release Test Matrix

| Check | Result |
|---|---|
| Backend tests | Verified: 112 passed |
| Frontend lint | Verified |
| TypeScript | Verified |
| Production build | Verified locally, CI and Vercel |
| Migration test | Verified in PGlite, not hosted Supabase |
| Browser smoke | Verified private and demo workflows |
| Demo mode | Verified UI and API write restrictions |
| Preview deployment | Verified anonymous desktop/mobile |
| Production deployment | Verified Services build and public UI |
| Production API | Verified readiness, listings, analytics, provider health, exports |
| Production mobile | Verified 390px routes/details, no horizontal overflow |
| CI on main | Verified linked release run; final docs SHA in handoff |
| Daily cron | Not configured: immutable snapshot mode |
| Supabase persistence | Not verified: InternAI credentials unavailable |
| Optional AI | Implemented/tested; production model not configured |

[Deployment](DEPLOYMENT.md) · [Resume and interview guide](RESUME_PROJECT.md) · [Historical V3 evidence](RELIABILITY_V3_REPORT.md)
