# V2 Baseline Audit

Inspected 2026-09-26 at commit 1a484cf before development. Eight baseline tests passed.

## Existing functionality retained

Eight modular providers, FastAPI discovery/jobs/export endpoints, Pydantic validation,
local JSON and Supabase storage, source merging, first/last-seen metadata,
React dashboard with expandable rows, CSV/XLSX, and historical documentation.

## Highest impact findings

1. GitHub, Simplify and Greenhouse invented paid compensation. Program catalogs
   invented posting dates and remote status. RemoteOK confused logos with websites.
2. Same company plus one overlapping engineering keyword merged distinct requisitions.
   Repeated fetches incremented source counts even without new sources.
3. Constructing the repository could delete legacy records. Local run/raw persistence
   was a no-op. Supabase and local merge behavior diverged.
4. Candidate skills were hard-coded. No profile API or writable application tracker.
   Ranking ran before trust in discovery. Unknown metadata produced misleading labels.
5. Provider errors were swallowed; detail fetching had no concurrency bound.
   Dry-run discovery still wrote run and raw records.
6. No authentication boundary for personal data; no RLS in schema; exports accepted
   spreadsheet formulas; upload validation and pagination were absent.
7. Frontend library files and lockfiles were accidentally ignored. Lint was unconfigured.
   Dashboard mixed salary currencies/periods using guessed conversion factors.
8. Historical tests asserted a false merge and personalized scores from hard-coded skills.

## Scope

Preserve the stack and provider interfaces. Implement a coherent single-user core:
profiles, classification fallback, explainable ranking, eligibility uncertainty,
conservative merges, tracking, discovery diagnostics, exports, analytics, and UI.
Multi-user authentication, embeddings, alerts and auto-apply remain outside this upgrade.
Historical audit volume figures are snapshots, not current daily throughput.
