# InternAI Current Status

Verification date: October 5, 2026 (Asia/Kolkata). This is the current release document; historical audits describe earlier stages.

- Baseline main: `687b3c7`, PR #1 already merged. Final release work is on `release/resume-ready-v1`; no duplicate V3 merge.
- Backend: **112 tests passed**, expanded from a reproduced 95-test baseline. One Starlette/httpx deprecation warning.
- Frontend: clean npm install, lint, typecheck and production build passed. Node middleware is compatible with Vercel Services.
- Migration: repeat V2/V3 schema/RLS/RPC tests passed locally in PGlite; no hosted database certification.
- Browser: private fixture discovery/tracking/reload/export and read-only demo passed at 1440px desktop / 390px mobile. Demo checks cover eight routes, search, details, disabled controls, blocked mutation requests, API readiness and screenshots without recorded runtime/API errors.
- Public source snapshot: October 5 IST (2026-10-04T19:44:00Z), 68 returned, 67 accepted including seven catalogs, 66 unique / 59 active-looking leads, 15 pay evidence, two remote, one explicitly India-compatible, zero quarantined, zero provider failures. RemoteOK yielded zero accepted internships; public YC coverage was degraded; trackers supplied thin leads. Counts are not daily volume.
- Demo: immutable sanitized real public records and generic profile. Private resume/profile/notes/contact/tracking data are not loaded. Both API layers reject writes; adapter rejects direct writes.
- Preview: Next.js + private FastAPI built successfully; authenticated proxy readiness/runtime reads passed. Anonymous preview browser verification awaits explicit approval of preview protection settings. Initial build failed on Edge middleware and was repaired, not hidden.
- Production URL: https://internai-oceankumars-projects.vercel.app (not yet production smoke-verified at this documentation checkpoint).
- Supabase: **Not verified; credentials unavailable for InternAI**. ContextIQ's separate hosted database was not reused. Writable production requires Supabase; no ephemeral JSON fallback.
- AI: optional validated integration implemented and fixture tested; production model not configured. Numerical ranking remains deterministic.
- Daily cron: **Not installed** for immutable snapshot demo. Durable persistence is required first. Lease-protected discovery CLI remains available; daily yield unknown.
- Security: no secret references or test tokens found in built browser assets. Production npm audit: zero advisories; full audit: five development-only lint dependency findings. Uploaded snapshot contains no personal tracking/notes/contact data.
- Main CI / exact production SHA: recorded in the final release handoff after verified merge. A source document cannot embed its own final commit hash; GitHub main and the release tag are authoritative.

[Deployment](DEPLOYMENT.md) · [Resume and interview guide](RESUME_PROJECT.md) · [Historical V3 evidence](RELIABILITY_V3_REPORT.md)
