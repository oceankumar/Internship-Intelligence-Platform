# InternAI Deployment

Current [Vercel Services](https://vercel.com/docs/services), not experimentalServices: frontend/ is Next.js; backend/ is FastAPI with `app.main:app`. Root rewrite exposes only frontend. Its [binding](https://vercel.com/docs/services/bindings) injects BACKEND_URL at runtime; API_TOKEN authorizes internal requests. Binding reachability alone is not authentication.

## Modes

- Public demo: both services set PUBLIC_DEMO_MODE=true. Backend reads only backend/demo/snapshot.json, never owner profiles, notes, contacts or tracking history. Proxy and backend deny mutations; adapter rejects direct writes. Uploads and discovery are disabled.
- Local private workspace: loopback JSON development persistence; existing remote password and host/origin boundaries remain.
- Writable production: APP_ENV=production requires API_TOKEN and configured Supabase. There is no local JSON fallback. Hosted backup/migration/RLS/RPC/concurrency tests are required before claiming persistence.

API_TOKEN is generated and stored as a Vercel secret. Do not set BACKEND_URL manually. Backend ALLOWED_HOSTS can be broad only for the unexposed token-authenticated service; frontend still validates exact generated hosts and same-origin requests. Browser authorization is never forwarded as the backend credential.

## Release Verification

Use explicit `--target preview` on initial deployment: Vercel otherwise treated this new project's first attempt as production. That attempt failed before publishing because Services rejected Edge middleware. Node middleware repaired compatibility. Failed deployments are not counted as a release.

Validate proxy readiness, search, filters, detail explanations, mutation restrictions, screenshots and logs before main merge. Then merge tested PR, wait for main CI and deploy exact clean main source. Git integration should use main as production branch.

Preview protection is separate from demo safety. Project-wide protection changes require approval. Supported authenticated `vercel curl` checks work while protection is enabled.

## No Cron In Snapshot Mode

A daily cron requires durable Supabase storage, a protected trigger and hosted discovery validation. An ephemeral crawler cannot persist results reliably. Existing lease-protected CLI remains scheduler-ready; no production schedule or daily yield is claimed.

## Verification

Run `DEMO_URL=<deployment> node scripts/demo-check.mjs` in frontend. SCREENSHOT_DIR can isolate deployed artifacts. Check /api/health, /api/ready, /api/internships, /api/analytics/market and /api/providers/health through Next.js. FastAPI has no public rewrite.

No new Supabase migration is needed for demo mode. V2/V3 schema/RLS/RPC tests remain in CI. Optional AI is unconfigured; deterministic ranking works without it. The full npm audit reports five development-only lint dependency findings; production dependency audit is clean as of this verification.
