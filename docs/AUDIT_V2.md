# Implementation Audit and V2 Upgrade

Audit date: September 27, 2026. Baseline: `1a484cf`.
Development branch: `feature/ai-internship-platform-v2`.
This report distinguishes baseline defects, implemented corrections, measured
behavior, and remaining work. The June report is historical, not current evidence.

## Executive Findings

1. **P0 before public deployment: this remains a single-owner product.** Local
   access is loopback-only by default. Server API tokens, host/origin checks and
   optional password-protected remote workspace access now exist. There is no
   account system or per-user ownership. Do not publish as a multi-user service.
2. **P1 corrected: invented compensation and destructive storage behavior.**
   Three providers previously emitted generic paid stipends. Local reads could
   delete records. These behaviors are removed. Historical generic paid values
   from those providers are treated as unverified when loaded, without modifying
   the file merely by reading it. The two existing sample records are preserved,
   marked, and hidden from normal results.
3. **P1 corrected: distinct jobs could merge.** Same company plus loosely related
   engineering titles is no longer enough. Source count measures unique providers.
   Notes, status, first-seen dates, favorites, contacts and corrections survive merges.
4. **P1 outstanding: discovery coverage is uneven.** The live public-source probe
   yielded 66 accepted records, but seven are program catalog entries, most are
   not explicitly remote, and the general YC page had no internship candidates.
   A snapshot cannot substantiate 50-100 fresh suitable opportunities per day.
5. **P1 before larger deployment: database-side search/ranking and tenant ownership.**
   Response pagination exists, but the backend still loads and scores the full
   collection. New indexes prepare the schema; they do not fix this read path.
6. **P2: scoring needs calibration, not claims of predictive accuracy.** The new
   formulas are explainable heuristics. No labeled evaluation set or outcome-based
   precision measurement exists. The optional LLM has not been tested against a
   real configured model in this workspace.

## Scope and Evidence

Inspected backend routes, models, all eight providers, normalization, deduplication,
trust, ranking, repositories, exports, frontend, dependencies, SQL, tests and docs.
Baseline had eight passing tests. V2 adds targeted regression/API/provider tests.
The local database initially contained 195 records, including two sample IDs.
Supabase credentials are not configured in this workspace. No production database
was read or changed. Live provider probes used a temporary empty repository and
`persist=false`; they did not add test or scraped records to the user's collection.

Key implementation paths:

- `backend/app/providers/`: live source adapters and shared request controls.
- `backend/app/pipeline/`: deterministic parsing, filtering, matching and lifecycle.
- `backend/app/services/ai.py`: optional validated classification and cache.
- `backend/app/services/repository.py`: local/Supabase storage and personal state.
- `backend/app/services/search.py`: filters, query parsing and sorting.
- `backend/app/main.py`: API/access boundaries and resume extraction.
- `supabase/schema.sql`, `supabase/migrations/202609260001_intelligence_v2.sql`.
- `frontend/components/`, `frontend/app/api/[...path]/route.ts`.

## Provider Inventory

No enabled adapter manufactures demo jobs. Live metadata is not the same as a
verified current opening. Program directories are especially important to separate.

| Provider | Data mode | Exact fetch and parsing | Main failure points |
|---|---|---|---|
| RemoteOK | Live public JSON | One `GET https://remoteok.com/api`; ignore legal/header objects, scan position/description/tags, query-filter, cap returned records; pipeline confirms internship | General remote feed contains few internships; no historical pagination; query mentions can be false positives; missing salary/date fields |
| YC Jobs | Live public HTML and JSON-LD | `GET https://www.ycombinator.com/jobs`; parse `[data-page]` JSON `props.jobPostings`; select internship candidates; fetch their YC URLs sequentially and parse `JobPosting` JSON-LD | General page is a 20-job sample, not exhaustive; currently all full-time; structured property changes; detail failures retain limited listing metadata; not a full YC internship feed |
| Work at a Startup | Disabled | No network request in V2; explicit disabled result | Historical HTTP 406. Requires a legitimate supported integration; not bypassed |
| Wellfound | Disabled | No network request in V2; explicit disabled result | Historical HTTP 403/anti-bot protection. Requires approved access; not bypassed |
| SimplifyJobs | Live community tracker | `GET https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md`; parse HTML `tbody tr`, inherit company for continuation rows, inspect closed markers, keep application URL | Season-specific path, changed table columns, stale tracker dates, missing detailed requirements/pay; tracker recency is not authoritative employer posting time |
| GitHub trackers | Live community trackers | Sequential GETs of `speedyapply/2026-SWE-College-Jobs/main/README.md`, `.../INTERN_INTL.md`, `vanshb03/Summer2026-Internships/main/README.md` on `raw.githubusercontent.com`; parse table columns and application links | Repository renames, table drift, overlapping upstream listings, partial failures; inferred year on month/day dates; early cap can favor first tracker |
| Public datasets | Live-fetch catalog, not live-opening feed | `GET https://raw.githubusercontent.com/deepanshu1422/List-Of-Open-Source-Internships-Programs/master/README.md`; parse program links, timeline and eligibility columns | Program may be closed or annual; no opening verification; stipend text may describe prizes; now explicitly labeled as catalog/unknown opening |
| Startup career pages | Live Greenhouse public API | For configured boards, `GET https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true`; parse jobs and full content; word-boundary internship title selection before limit | Board removal/renaming, non-Greenhouse careers, uneven board coverage, partial board failures; `updated_at` is not treated as posting date |

Default Greenhouse boards: stripe, reddit, gitlab, anthropic, figma, vercel.
Board order can bias a capped run. The provider list is operator configuration,
not broad coverage of all startups.

### Measured Volume

Final read-only probe: **2026-09-27 11:03:10 UTC**, query `internship`,
maximum 20 records returned per provider, default empty candidate profile.
"Fetched" below means adapter-returned records after adapter query/title checks,
not the entire upstream feed. Durations include time waiting for a concurrency slot.

| Provider | Fetched | Accepted | Paid evidence | Remote | Duration | Observed state | Current unique new jobs/day |
|---|---:|---:|---:|---:|---:|---|---|
| RemoteOK | 1 | 0 | 0 | 0 | 1.9s | HTTP/parser succeeded, record rejected | Unknown |
| YC | 0 | 0 | 0 | 0 | 3.1s | Degraded: no candidates in general page | Unknown |
| Work at a Startup | 0 | 0 | 0 | 0 | n/a | Disabled, not probed | 0 through this connector |
| Wellfound | 0 | 0 | 0 | 0 | n/a | Disabled, not probed | 0 through this connector |
| Simplify | 20 | 20 | 0 | 0 | 3.0s | Healthy fetch, capped | Unknown |
| GitHub trackers | 20 | 20 | 0 | 1 | 3.4s | Healthy fetch, capped | Unknown |
| Program catalog | 7 | 7 | 0 | 0 | 4.4s | Catalog reachable, openings unverified | Not an opening-volume metric |
| Greenhouse | 19 | 19 | 9 | 0 | 9.5s | Healthy fetch | Unknown |

Totals: 67 fetched, 66 accepted, one rejected, nine with paid evidence, one remote,
zero observed duplicates, zero failing enabled providers, two disabled providers.
Seven accepted records are catalog opportunities rather than verified job openings.
Zero duplicates does not establish perfect deduplication; descriptions are often
too thin to justify cross-source merging. No populated profile was used, so this
probe is not a personalized recommendation-quality benchmark.

**Daily volume cannot be confirmed.** There is no scheduled 24-hour collection
history in the local workspace. Existing discovered dates are historical ingestion
timestamps, not proof of daily upstream supply. Measure per-provider first-seen
canonical jobs across repeated runs, in a defined UTC/day window, separate from
re-fetched records, changed records, catalog programs and source posting dates.
Do not multiply this capped snapshot by the number of scheduled runs.

### Rate Limits and Failure Isolation

No fixed upstream quota was verified for these public endpoints. GitHub REST API
quotas must not be presented as quotas for `raw.githubusercontent.com`; likewise
Greenhouse Harvest quotas are not automatically Job Board API quotas.

Implemented controls in `providers/base.py` and `pipeline/runner.py`:

- Default two simultaneous providers, one-second minimum request spacing per host.
- Successful responses cached for one hour, process-local, bounded to 500 entries.
- HTTP timeout 20 seconds; provider deadline `max(30, timeout * 6)` seconds.
- One retry for 429/502/503/504. Honor numeric Retry-After up to five seconds;
  longer or HTTP-date values stop this run rather than sleeping indefinitely.
- At most three redirects. Transparent configured bot user-agent.
- Discovery API has one-process lock and 60-second cooldown.
- Failure of one provider does not cancel others. HTTP errors, warnings,
  rejection reasons, duration and counts are included in run diagnostics.

Remaining: cooldown/cache/locks are not distributed; multiple workers would bypass
the intended global limit. HTTP-date retry scheduling and durable backoff are not
implemented. A healthy fetch means transport/parsing worked, not that a job is
current, safe, eligible or paid. Partial-fetch adapters can be degraded, not failing.

## Trust Scoring

### Baseline Algorithm

Baseline starts at 20. Add website 25, a URL containing `linkedin.com` 15,
20-word company description 15, product/customer terms 15, team/hiring terms 10.
Clamp 0-100; suspicious below 50; substring blacklist forces zero/excluded.

Weaknesses: any syntactically valid URL earned credit, even a logo URL. A malicious
hostname containing `linkedin.com` could qualify. Self-authored boilerplate earned
most points. Sparse legitimate companies were penalized. Job-level signals were
stored as company trust. Scoring order meant trust could be stale during ranking.

### V2 Algorithm

Baseline 30; valid HTTPS application URL +10; recognized ATS +25 or recognized
public board +20; supplied company domain agrees with application domain +15;
job description at least 80 words +15; named company +5. Invalid/nonpublic link
-30; URL shortener -25; application-payment language -65; messaging-only hiring
-30; guaranteed earnings claim -25. Clamp 0-100. Configured exact company/domain
exclusions force zero and hidden/rejected. Suspicious below configurable 40.
Levels: high >=80, moderate >=50, review otherwise. Reasons include contributions.

Trust is evaluated before priority. UI says domain agreement, not independently
verified company identity. URLs are displayed as text/links, never injected HTML.

### Remaining Weaknesses and Improvements

- HTTPS and ATS hosting are weak authenticity evidence, not proof against scams.
- Domain matching uses source-supplied data, not verified ownership. Exact policy
  exclusions can miss aliases; substring matching risks false accusations.
- Regexes can misunderstand negation, e.g. a statement that a company never asks
  for payment. A low score should trigger review, not a factual accusation.
- No domain age/reputation, redirect-chain audit, contact-domain verification,
  copied-description detection, or independent source corroboration.
- The company table still carries a job-influenced trust summary. Separate
  company evidence and listing evidence before multi-user/shared scoring.

Priority: build a labeled safe/suspicious review set; distinguish missing evidence
from negative evidence; persist evidence URL/time/confidence; add domain ownership
and contact matching only with reliable sources; calibrate false positives before
changing thresholds. Do not use an LLM as the final legitimacy authority.

## Relevance, Eligibility and Opportunity

### Baseline Algorithm

Start 20; React +15, Next.js +10; frontend/web title +15 (otherwise web skills +10);
remote +15 or hybrid +5; paid +15, unpaid -20, unknown -5; startup text +10;
student terms +5; AI terms +5. Experience >=2 years loses up to 30; avoidance
keywords lose up to 20; named training/scam keywords -50; trust adjusts -10/+5.
Clamp 0-100. Apply Today requires >=80 and paid/nonsuspicious; Apply This Week >=60.
Matching/missing skills used the hard-coded `OCEAN_SKILLS` set, but actual overlap
did not drive the numerical score. Company age could be mistaken for experience.

This was directionally frontend-focused but not reliably personalized or suitable
for an individual student. Keyword presence inflated fit, degree/geography were
missing, and unknown pay/source data distorted distribution.

### Current Deterministic Match Formula

`match = skills(40) + role(25) + experience(15) + remote(10) + compensation(10)`.

- Skills: proportion of required skills present in the editable profile. Missing
  job/profile skills receive 40% of the skill component, explicitly uncertain.
- Role: full weight for preferred role family, 30% otherwise.
- Experience: full weight if stated minimum is met, zero on conflict, 60% if unknown.
- Remote: full weight when preference is met/not required, half for hybrid/unknown,
  zero for onsite when remote is preferred.
- Pay: full when paid/not required, half unknown, zero unpaid when paid preferred.
- Explicit eligibility conflict caps the score at 49 using a visible deduction.

Eligibility: explicit experience and graduation ranges plus limited US restriction
recognition. Likely Eligible 90 with explicit fitting evidence, Unclear 60 with
missing information, Likely Not Eligible 20 with conflict. It never declares
absolute eligibility. Citizenship is not inferred from country.

`opportunity = round(match*.45) + round(eligibility*.20) + round(trust*.15)
 + round(freshness*.15) + round(urgency*.05)`.

Freshness uses actual posting age where available, otherwise lower-confidence
discovery age. A deadline within seven days adds urgency. Expired/closed or unseen
90 days becomes inactive; unseen 30 days is stale. A capped source omission does
not prove closure. A new record is not automatically a newly posted role.

Priorities: Apply Now requires match >=80, likely eligible, trust >=65, paid and
a populated skills profile. Strong Match requires >=70, no eligibility conflict,
nonsuspicious trust and populated skills. Worth Exploring >=45, otherwise Low Match.
Hidden/excluded/inactive jobs are not normal recommendations.

### Reproducible Examples

Profile: React + JavaScript, frontend preference, three months experience,
graduation 2029, India, paid/remote preferred. Newly posted example has trust 60
(HTTPS + supplied domain match + named company), no deadline urgency.

| Scenario | Match | Eligibility | Opportunity | Reason |
|---|---:|---:|---:|---|
| Frontend, React/JS, paid/remote, 0 months minimum, graduates 2028-2030 | 100 | 90 | 87 | All match factors fit; Strong Match because trust is below Apply Now threshold |
| Same job, but profile lists Java/backend only | 43 | 90 | 61 | No skill overlap, role component 8; Low Match despite eligibility |
| Same frontend fit, two years required | 49 | 20 | 50 | Experience conflict; visible cap prevents high-fit presentation |
| Same high fit, unpaid and onsite | 80 | 90 | 78 | Loses 20 preference points; retained, not deleted |

These are deterministic fixtures, not real employer recommendations or validated
success probabilities. Exact totals can change with age/freshness.

### Student Suitability and Next Improvements

Much better for a frontend student: editable skill inventory, real overlap,
missing skills, explicit experience/graduation checks and visible uncertainty.
Still incomplete: preferred locations/education are stored but not fully scored;
work authorization, degree level, student year, age and timezone need structured
requirements. Required/preferred skill parsing is a limited vocabulary. A description
mention is not always a requirement. Semantic equivalence and transferable skills
are not modeled, and long skill lists can dilute otherwise useful roles.

Next: label at least 100 representative frontend/student opportunities; measure
precision@10, rejection false positives, eligibility conflicts and unknown-field
rates. Separate must-have vs preferred skills with evidence; score location/work
authorization separately; show confidence independently of desirability. Reweight
only after evaluation, not simply to increase the Apply Now count.

## AI Boundary

Optional chat-completions-compatible provider, Pydantic output schema, exact quote
evidence, confidence threshold and content-hash cache. Only description-supported
skill classifications affect ranking inputs. Other proposed classifications remain
in provenance for review; model-generated scores/pay/eligibility never override
deterministic facts. Failure/invalid JSON/low confidence uses existing deterministic
results. AI is disabled by default and skipped on write-free probes.

No embeddings, vector search, model-selected numerical scores or model-quality
claims. Natural-language search is a deterministic parser for supported role,
skill, remote and paid terms; it is not arbitrary semantic understanding. Resume
analysis is deterministic PDF/text extraction, not an LLM upload. Current extraction
covers recognized skills and education lines, not reliable work/project timelines.

## Database Review

Baseline tables: companies, job_sources, jobs, job_skills, trust_scores, tags,
company_exclusions, discovery_runs, raw_jobs. Jobs already held lifecycle/source
arrays and tracking columns. Existing arrays plus job_skills and trust_scores
duplicate concepts; not all tables were maintained by actual writes.

V2 migration is additive except replacing overly strict indexes/checks. It adds
normalized title, role/country, scores, lifecycle/deadline, favorites/hidden,
comparable stipend units, extensible intelligence JSON, full-text search document,
private profile/search/AI state and run-details JSON. Updates are transactional RPCs.
Legacy IDs and personal tracking are preserved. Supabase run/raw writes continue in
the existing dedicated tables rather than replacing their history.

Indexes cover company FK, active/opportunity ordering, role/country, source arrays,
deadline, application state, full-text terms and run chronology. URL uniqueness is
case-sensitive because URL paths can differ by case. Website is not a unique
company identity. Shared merge logic is used by both storage modes.

All public tables enable RLS; anon/authenticated access and privileged RPC execution
are revoked; server service-role credentials retain access. This intentionally
supports a private backend, not browser-direct authenticated client access.
See [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security)
and [database functions](https://supabase.com/docs/guides/database/functions).

### Scalability and Phase 2 Work

1. **High:** filtering/ranking loads all jobs, then paginates. Move canonical search
   to indexed SQL, materialize profile/version-specific scores, use keyset pagination
   and test query plans. Adding indexes alone is insufficient.
2. **High:** JSON merge scans are roughly O(existing * incoming); add URL/source-ID
   maps and indexed candidate retrieval before fuzzy comparison. Local JSON is for
   one host only; whole-file rewrites are unsuitable for large/shared deployments.
3. **High:** no tenant IDs or user/job junction. Split candidate profiles, application
   state and per-profile scores from globally shared job records before multi-user use.
4. **Medium:** JSON and typed columns can diverge. Define a single authoritative field
   contract and update all query-critical score/tracking columns transactionally.
   Some legacy score columns remain compatibility fields, not fresh materializations.
5. **Medium:** company canonicalization does not solve subsidiaries/aliases. Add a
   curated alias table; don't make all jobs sharing an ATS domain one company.
6. **Medium:** PostgreSQL raw/run/AI history has no automated retention job. Set
   operator-approved retention, expiry cleanup, backups and size monitoring. Local
   diagnostics are bounded (100 runs, 10 raw snapshots, 1,000 AI cache entries).
7. **Medium:** one-process discovery locks/cooldowns are not distributed. Use a
   queue or advisory locks before adding workers or scheduled overlapping runs.
8. **Medium:** no live Supabase/PostgREST integration test was possible without
   credentials. Local SQL verification covers schema/RPC/RLS, not deployed gateway,
   network latency, connection pooling or existing production policy interactions.

## Prioritized Follow-Up

| Priority | Fix | Impact / acceptance criterion |
|---|---|---|
| P0 before multi-user/public launch | Tenant auth/ownership and upload resource isolation | Cross-user API/RLS negative tests; isolated bounded PDF worker; TLS/access controls |
| P1 | Improve legitimate internship source coverage | Validated current-year trackers and employer feeds; >=7 days unique/day telemetry |
| P1 | Indexed SQL search and versioned per-profile scores | Representative query plans/latency at 10k and 100k records; no full collection scan per page |
| P1 | Structured eligibility and skill evidence | Labeled evaluation; geographic/degree conflicts never hidden by a high skill score |
| P2 | Domain evidence and trust calibration | False-positive review set, dated evidence and explainable confidence |
| P2 | Distributed collection and retention | No duplicate overlapping runs; bounded history and tested backup/restore |
| P2 | Broader provider fixtures and drift alerts | Season/schema changes detected before silently losing coverage |
| P3 | Alerts, semantic search, richer resume parsing | Only after core daily coverage and matching quality are measured |

## Verification Boundaries

Automated coverage includes normalization, salary units, word-boundary filtering,
profile scoring, conflicts, dedupe false merges, personal state preservation,
dry-run isolation, AI validation/fallback/cache, provider fixtures, retries/cache,
API pagination/filtering, notes/status/corrections, exports and upload rejection.
SQL tests execute the real base schema/migration in PGlite (PostgreSQL WASM), twice,
with legacy data, RPC writes, role grants and RLS checks. They are not a live
Supabase deployment test. Browser fixtures are explicitly labeled and isolated.

No deployment, push, merge, live database migration, automatic applications or
third-party protection bypass was performed.
