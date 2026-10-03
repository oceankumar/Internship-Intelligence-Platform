# Current Status

Last local verification: 2026-10-04 (Asia/Kolkata). This file supersedes historical status claims.

- Backend: 95 regression tests passed; one Starlette/httpx deprecation warning remains.
- Frontend: lint, typecheck and production build passed; desktop 1440px and mobile 390px fixture workflow passed with no console/API errors.
- Real application: 59 visible, non-sample active-looking internships reached the UI after bounded persisted discovery. Original 195 records were retained; 62 new records were added and 5 incoming records updated/merged, leaving 257 stored records.
- Live probe: six enabled sources tested individually and together, cap 20/source. 68 returned, 67 accepted including 7 catalogs, 66 unique records, 59 unique active-looking internships, 15 with source pay evidence, 44 compensation unknown, 2 remote, 1 explicitly India-located. No Strong Match or Apply Now for the explicit frontend-student evaluation persona.
- Providers: Greenhouse yielded 20 substantial descriptions; Simplify/GitHub supplied thin tracker leads; RemoteOK supplied no accepted internships; YC public page supplied zero internships among its 20 exposed postings; catalog openings are unverified. Wellfound and Work at a Startup remain disabled.
- Application links: six checked; four roughly corresponded, one was reachable but needed manual review, one returned 403. No observed 404/410; unverified is not valid or dead.
- Daily new internship supply: unknown. No recurring discovery is installed; a lease-protected CLI entry point is available.
- Supabase: NOT live verified, credentials unavailable. Local PGlite tested schema, repeat migration, score authority, leases, tracking preservation and transaction rollback.
- AI: not configured. Deterministic extraction and ranking work without it; fixtures verify fallback only.
- Security: listing quarantine is separate from company identity; default discovery excludes quarantined/blocked records. Resume PDF parsing runs in a disposable CPU/time-bounded process, with a Linux memory cap.
- Scope: personal local discovery/tracking, not multi-user or production certification. No applications are automatically submitted.

Detailed evidence, algorithms, remaining blockers and prioritized fixes: [Reliability V3 Report](RELIABILITY_V3_REPORT.md).
