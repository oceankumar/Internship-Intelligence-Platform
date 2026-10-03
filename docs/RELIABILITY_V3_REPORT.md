# Internship Platform Reliability V3 Report

Verification date: October 4, 2026, Asia/Kolkata. Branch: `feature/internship-platform-reliability-v3`.
This is implementation and local acceptance evidence, not a production certification.
The prior detailed audit remains in [AUDIT_V2.md](AUDIT_V2.md); historical claims there are snapshots, not current status.

# 1. DID THE PRODUCT WORK BEFORE THE CHANGES?

The local prototype worked with controlled fixtures: 53 backend tests, lint, TypeScript, production build, repeated SQL migration and desktop/mobile browser workflow passed. The original local store held 195 records, including two historical samples, but zero visible active jobs. No stored candidate profile or discovery history was available. Hosted Supabase and live AI credentials were absent.

The reproduced capped baseline returned 68 candidates, accepted 67 including seven unverified catalogs, and had 64 unique records after dedupe. Paid evidence existed on six returned records. This was a one-off read-only snapshot, never a daily-volume measurement. The product's discovery-to-tracking mechanics worked; daily useful supply did not have evidence.

# 2. WHAT WAS ACTUALLY BROKEN?

- Explicit fee/messaging scam signals reduced trust but did not reliably remove listings from default discovery.
- Unknown requirements/experience received positive scoring credit. Weak required coverage could receive a strong label.
- Every extracted technology mention could become required; broad aliases and description boilerplate inflated skill/geography claims.
- Search could discard country or other residual terms, particularly short queries.
- The normal stipend-sort control could request a comparison without currency/period and receive 422.
- Catalogs could count as current inventory without known opening state.
- Trackers assumed fixed columns and sequential sampling; some current headers differ. YC's exposed 20-posting page is not complete coverage.
- SQL legacy match/priority fields could disagree with intelligence JSON; company evidence was mixed with listing risk.
- Discovery coordination was process-local, stale runs were not recovered, and hosted completion was not one transaction.
- Saved-search deletion and correction reset were missing from UI; profile/search loading failures could be swallowed.

# 3. WHAT DID YOU FIX?

High impact: separate listing risk and company identity evidence; default quarantine exclusion including legacy `/api/jobs`; clause-aware fee negation; deterministic fit/confidence/preference semantics; skill coverage caps; country/region/authorization/degree explanations; preserve residual search constraints; prevent incomplete stipend requests; catalog inventory separation.

Reliability: configurable provider enablement and seasonal URLs, header-aware shared tracker parser, fair source/board sampling, Greenhouse job details/pay transparency, truthful low-yield states, explicit YC coverage warning, typed SQL score synchronization, source-instance identities, owner/expiry leases, interrupted-run recovery, bounded run duration and transactional Supabase completion.

UX and verification: listing-level trust and confidence explanations, distinct Recently Posted/Newly Discovered, saved-search deletion with confirmation, source-value correction reset, visible retry states, expanded sorted formula-safe exports, readiness endpoint, isolated PDF parser, scheduler-ready CLI, synthetic benchmark, product smoke script and CI checks without live-provider dependency.

Further real-data review removed generic company 'worldwide' and incidental remote-employee claims as remote eligibility evidence, avoided brand-tool and learnable-language requirements, corrected cross-domain Greenhouse requisition dedupe, and prevented likely-ineligible jobs from receiving Worth Exploring.

## Current Algorithms

Match components: required skill coverage 40, role preference 25, explicit experience fit 15, remote preference 10, paid preference 10. Unknown requirements and experience get zero credit. If required and preferred skills are both known, preferred coverage occupies 5% of the skill component. Unknown requirements cap match at 59; <75% coverage caps at 64; known eligibility conflict caps at 49. Geography mismatch also caps and blocks strong labels.

Fit = skills/role/experience subtotal /80 *100; null if requirements are unknown. Evidence completeness = required skills 40 + substantial description 20 (thin 5) + explicit experience 10 + degree/graduation 10 + geography 10 + known compensation 10. This is a heuristic, not calibrated confidence. Paid/remote/geography/role compliance is shown independently as matching, conflicting or unknown.

Opportunity weights: match 45%, eligibility 20%, listing trust 15%, freshness 15%, urgency 5%. Each component is rounded. Posting date is preferred for freshness; unknown posting dates receive a conservative last-seen-based fallback. New discovery is based on first_seen, not posting date. Strong Match needs match >=75, >=75% skill coverage, completeness >=65, normal risk, aligned preferences and no explicit eligibility conflict. Apply Now additionally needs match >=85, likely eligibility, listing trust >=65 and completeness >=80. Numeric scoring never comes from AI.

Company identity evidence: baseline 30, HTTPS 10, recognized ATS 25 or known board 20, supplied website/apply domain agreement 15, named company 5, capped 100. Long listing text no longer boosts company identity. Listing risk subtracts 50 per high-risk reason (capped 100); shorteners add 25 and require review. Invalid URLs/exclusions block. Explicit fees, messaging-only recruitment or guaranteed earnings quarantine regardless of ATS bonus. These are auditable signals, not verified identity or legitimacy probabilities.

Remaining algorithm weaknesses: regex section boundaries, alternative skill lists ('one of Java/Python/etc.'), incomplete geography/degree taxonomy, no visa verification, uncalibrated evidence and ranking weights, domain/ATS identity spoofing limits, no independent company verification, unknown experience often penalizing legitimate graduate roles. Improvements should use labeled source excerpts and eligibility cases, not raise scores to manufacture strong results.

# 4. REAL DISCOVERY TEST

Six enabled providers were tested individually then together, cap 20/source. Two restricted providers were checked as disabled without requests. The combined run reused in-process cache from individual checks; it is not an independent repeat sample. Final public-source snapshot: `2026-10-03T20:53:47Z` (October 4 IST).

| Provider | Returned | Accepted | New in empty probe | Paid | Remote | Active rows | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| RemoteOK | 1 | 0 | 0 | 0 | 0 | 0 | Low Yield; non-internship rejected |
| YC Jobs | 0 | 0 | 0 | 0 | 0 | 0 | Degraded; coverage limited to 20 public postings |
| SimplifyJobs | 20 | 20 | 20 | 0 | 1 | 20 | Low Yield; thin tracker metadata |
| GitHub trackers | 20 | 20 | 19 | 7 | 1 | 20 | Low Yield; thin metadata, one duplicate |
| Program catalog | 7 | 7 | 7 | 0 | 0 | 0 | Low Yield; opening state unknown |
| Greenhouse | 20 | 20 | 20 | 8 | 0 | 20 | Healthy; substantial employer descriptions |
| Work at a Startup | 0 | 0 | 0 | 0 | 0 | 0 | Disabled |
| Wellfound | 0 | 0 | 0 | 0 | 0 | 0 | Disabled |

Totals: 68 candidates, 67 accepted including catalogs, 66 unique records, 59 unique active-looking internships, 15 with source pay evidence, 44 unknown pay, 2 remote (both US-restricted tracker leads), 1 explicitly India-located, zero quarantined in this live batch, zero Strong Match/Apply Now. Final re-ranking classifies all 59 as Low Match for the evaluation persona; this is not 59 suitable recommendations.

The separately persisted run against the original local store added 62 and updated/merged five incoming records. The 195 existing rows were preserved, leaving 257 rows and 59 normally visible active internships. 'New' in the empty probe is not new market supply or new today in an existing collection.

Active means recently observed, no known expiry/closed state, and no high-risk block. It does NOT mean every application page was checked.

## Fetch Paths, Failures And Limits

All enabled sources use live public content, not mock jobs. Fixtures exist only in tests. The program catalog is live static program data, not live application inventory.

| Provider | Exactly how fetched | Main failure points / coverage |
|---|---|---|
| RemoteOK | One GET `https://remoteok.com/api`; ignore header/legal objects; inspect title/tags or explicit internship role sentence; query-filter/cap; pipeline confirms internship | General remote feed, incidental internship tags, missing salary/geography; current candidate rejected. No historical pagination |
| YC | GET `https://www.ycombinator.com/jobs`; read `[data-page]` JSON `props.jobPostings`; title/type token checks; selective same-domain detail GET and JSON-LD JobPosting parsing | Only 20 public postings observed, no verified pagination endpoint, layout/JSON-LD drift and possible blocked detail requests. Zero internship yield in snapshot |
| Simplify | GET each `SIMPLIFY_URLS` README; HTML/Markdown table headers; company continuation, closed-row skip, dates/pay if present; round-robin selection | Seasonal branch/path, table drift, abbreviated locations, requirements absent; no bulk employer-detail crawler |
| GitHub | GET each `GITHUB_TRACKER_URLS`; same header-aware parser and fair interleave; retain tracker URL/apply URL/provider ID | Three seasonal default files; community pay claims not independently verified; generic URLs and mirrors require identities |
| Greenhouse | GET `https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true`; internship title candidates; fair board selection; GET `/jobs/{id}?pay_transparency=true`; preserve first_published rather than updated_at as posting date | Six configured boards only; no internship candidates on some boards; missing periods/experience; detail failure retains base listing with warning |
| Catalog | Public repository YAML/JSON entries through `public_datasets.py`; retain program descriptions and links | Static programs, stale cycles, unknown opening windows; excluded from default internship inventory |

Default tracker URLs are listed in `backend/app/config.py` and are operator configurable. Default boards: stripe, reddit, gitlab, anthropic, figma, vercel. Greenhouse request semantics were checked against [official Job Board API documentation](https://docs.greenhouse.io/job-board.html).

Internal limits: two concurrent providers; one second/request per host per process; 20-second default HTTP timeout; provider timeout max(30s, 6*HTTP timeout); total discovery timeout 150s, shorter than 900s lease; response cache one hour, maximum 500 entries; manual cooldown 60s. One retry for 429/502/503/504 only when numeric Retry-After <=5 seconds; longer/date headers stop retry. Host locks/cache are per-process, not a fleet-wide quota system. No 429 was observed in the final probe. Provider contractual quotas were not established; do not mistake internal throttling for permission or an official quota.

Current daily volume for EVERY provider: UNKNOWN. There is no installed daily scheduler or longitudinal run series. Zero yield today does not prove permanent zero supply.

# 5. REAL PRODUCT TEST

| Step | Result | Evidence boundary |
|---|---|---|
| Open app | ✅ | Real UI and isolated fixture smoke |
| Profile loads | ✅ | Empty real profile honestly displayed; editable fixture profile |
| Run discovery | ✅ | Persisted live CLI uses same runner as tested manual button |
| Internships appear | ✅ | 59 non-sample real listings in UI |
| Filter internships | ✅ | Roles, residual search and unit-safe stipend regression |
| Open details | ✅ | Desktop/mobile |
| Understand match | ✅ | Fit, completeness, preference and eligibility explanations present; subjective comprehension not measured |
| Apply using source | 🟡 | Links visible; six pages checked; NO applications submitted |
| Save internship | ✅ | Fixture persistence test |
| Mark applied | ✅ | Fixture status/date test |
| Add notes | ✅ | Fixture persisted notes |
| Reload application | ✅ | Tracking survived navigation/reload |
| Export records | ✅ | CSV/XLSX API; browser CSV; safe text cells and selected sort |

Screenshots were inspected at 1440px desktop and 390px mobile. The automated check visits all seven views, checks mobile horizontal overflow, dialog/filter access and captures runtime/API failures. Real UI verification was read-only and did not change personal favorites/status/notes.

# 6. RECOMMENDATION QUALITY TEST

Evaluation persona: frontend-focused B.Tech CS student, India, React/JS/TS/HTML/CSS/Git/Next.js, three months experience, remote/paid preference. This is an explicit evaluation profile, not an invented saved user profile. Graduation year was intentionally unspecified.

Twenty software/developer internship leads were reviewed. Judgment evaluates how honestly the ranking treats each lead; it is NOT precision among recommended jobs, because no Strong Match/Apply Now was produced.

Sample size: 20. Good: 6. Reasonable: 12. Poor: 2. Clearly wrong: 0 after label/geography corrections. Subjective one-reviewer evaluation, not calibrated model quality.

| Company / role / location | Final assessment | Rationale |
|---|---|---|
| Vercel SWE Summer '27, San Francisco | Good | JS/TS fit separated from explicit location conflict; now Low Match, not Worth Exploring |
| Vercel SWE Winter '27, San Francisco | Good | Same restriction; no globally remote inference from company boilerplate |
| Stripe high-school software internship, US | Good | University profile/level conflict and no false remote claim |
| Figma SWE Summer 2027, London | Poor | Alternative programming-language evidence still behaves like all required; overly harsh skill gaps |
| Figma SWE Summer 2027, US | Reasonable | Correct location caution; same alternative-language weakness |
| Figma SWE Winter 2027, US | Reasonable | Same evidence limitation |
| Stripe SWE, London | Reasonable | Generic language mentions do not invent mandatory stack; foreign relocation unclear |
| Stripe SWE, Bengaluru | Poor | Real relevant local software role gets Low Match because mandatory stack, pay and remote evidence are absent; conservative but not a useful shortlist |
| Stripe SWE, Singapore | Reasonable | Role relevant, requirements/pay/workplace uncertainty and relocation caution |
| Stripe SWE, Bucharest | Reasonable | Unknown country must be confirmed; no likely-eligible certainty from incomplete geography |
| Electronic Arts SWE, Austin | Good | Source page corresponds; thin tracker skills remain unknown, not highly scored |
| Databricks SWE, London | Good | Requisition mirrors merged; tracker requirements unknown |
| Arc SWE, Torrance | Reasonable | Thin evidence; no strong match manufactured |
| Harvey SWE, NYC | Reasonable | Same |
| Harvey SWE Summer 2027, SF | Reasonable | Same |
| Affirm SWE Machine Learning, SF | Good | Non-frontend specialization and unknown requirements lower score |
| Affirm SWE Summer 2027, SF | Reasonable | Thin evidence |
| xAI SWE Intern/Co-op, Palo Alto | Reasonable | Thin evidence |
| Mindex SWE Co-op, Rochester | Reasonable | Thin evidence |
| Walleye Special Projects Developer, NYC | Reasonable | Thin evidence |

Recurring problem is supply and requirement evidence, not a need to inflate numerical scores. Ranking is safer for a frontend student than before, but the current source mix is predominantly overseas general SWE/data roles and unknown-pay leads. It is not yet a proven paid-remote-India frontend recommender.

# 7. DATA QUALITY

- Inspected 20 rich Greenhouse descriptions and 30 tracker metadata rows. Titles/descriptions identify internships in those inspected samples (20/20 rich descriptions and 30/30 tracker titles); the tracker figure is title consistency, NOT employer-page classification precision or open-status accuracy. No accepted obvious full-time role was identified in these samples. RemoteOK's non-internship candidate was rejected.
- Pay evidence: 15 unique active records have source evidence: eight from employer Greenhouse content/pay data, seven from community tracker pay columns. All 15 were consistent with their ingested pay evidence; only eight are primary-source evidence. This is not 15 independently verified salaries. Missing periods stay unknown, so no unsupported cross-unit comparisons occur.
- Remote: two active records have explicit remote tracker locations; both restrict geography to the US. Source-label consistency 2/2; employer permission NOT independently verified. Removed one incidental remote-employee false positive found during employer-description review.
- Geography: exactly one explicit India location in the capped snapshot. Abbreviated/unsupported countries remain unknown; no relocation, visa or universal remote permission is assumed. Region mapping is incomplete and requires confirmation.
- Six apply links: four HTTP 200 pages roughly matched title/company; one HTTP 200 needed review; one 403 remained unverified. Zero observed 404/410/explicit expired pages. Do not report this as 6/6 valid. Known Greenhouse hostname migration and www-only redirects are allowed; unrelated redirects are flagged. Each hop gets public-DNS checks. The standalone check is not a production DNS-pinning/rebinding defense.
- Duplicate: one known Databricks Greenhouse requisition across two tracker mirrors was correctly merged. Remaining records were not independently labeled for duplicate ground truth; no recall/precision percentage is claimed.
- Skill extraction: company Figma mentions outside requirements and Vercel JS/TS requirement section issues were fixed using actual descriptions. Alternative required-language groups remain imperfect. No reliable skill precision percentage is claimed without a token/requirement-labeled ground truth.

Local raw evidence and full public descriptions are ignored under `backend/data/live-v3.json`; only summaries and reviewed findings are committed. They contain no resume or actual private profile. Application-page excerpts are bounded and not republished as full copyrighted pages.

# 8. SECURITY / TRUST

Quarantined/blocked listings cannot enter default discovery/recommendations/export/legacy safe list. They remain inspectable in authenticated/loopback developer routes or explicit include_risky. ATS evidence does not override dangerous listing text. Company identity is not globally poisoned by a scam-like listing. Negation/contrast, optional messaging, shorteners and invalid URLs have regression coverage. Regex detection can still miss sophisticated fraud and requires manual judgment.

URL normalization rejects credentials, non-http(s), local/private IP literals and local/internal host suffixes. Optional link checking resolves public DNS on every redirect and does not bypass 403/429, CAPTCHAs or antibot systems. Main browser links are not server crawlers. No automated submissions or form completion exist.

Resume uploads: MIME/UTF-8/PDF signature validation, 2MB limit, <=10 unencrypted PDF pages, empty/malformed rejection, 50k text cap. PDF parsing is disposable, eight-second wall limit, five-second CPU limit, 512MB address-space limit on Linux; macOS has no memory cap. No file paths supplied by user, no persistent upload, no full-content logs. Public multi-user deployment still needs upload concurrency limits and a stronger sandbox.

Secrets remain backend/server-side and ignored; `.env`, local data, credentials and resume data are not committed. Loopback/token, origin and frontend host/password boundaries remain intact. Git author email was explicitly approved and authenticated account ID checked before commits.

# 9. TEST RESULTS

Final checks are recorded in CURRENT_STATUS.md and the commit close-out. Verified before documentation close-out:

| Check | Result |
|---|---|
| Existing baseline pytest | 53 passed |
| Expanded pytest | 95 passed, one Starlette/httpx deprecation warning |
| lint | PASS |
| typecheck | PASS |
| production build | PASS, Next.js 15.5.26 |
| SQL migration | PASS: base schema, repeat V2/V3, typed scores, source instances, tracking preservation, role access, lease ownership, failed-completion rollback |
| Browser | PASS fixture desktop/mobile workflow; zero recorded console/API errors |
| Product smoke | PASS startup/readiness -> empty fixture store -> discovery -> UI -> tracking/reload -> export |
| Actual live UI | PASS 59 non-sample visible internships, desktop/mobile, safe links, no runtime/API failures |
| Live provider probe | Completed with truthful low-yield/degraded sources; not all sources useful |

One remaining test warning: Starlette's TestClient/httpx deprecation. No application error. Earlier smoke harness failures were an omitted allowed test host and inaccessible exact labels on pay selectors; fixed and rerun, not hidden. No hosted CI execution is claimed merely because a workflow file exists.

Synthetic performance on this machine (not a production load test):

| Jobs | Rank seconds | Filter seconds | Sort/page seconds | Merge 100 seconds | Peak process RSS |
|---:|---:|---:|---:|---:|---:|
| 1,000 | 0.194 | 0.002 | <0.001 | 0.063 | 68.6 MB |
| 5,000 | 1.006 | 0.009 | 0.002 | 0.228 | 161.3 MB |
| 10,000 | 1.721 | 0.021 | 0.005 | 0.456 | 308.8 MB |

These are component timings, not end-to-end database request latency. RSS is cumulative process peak on macOS, including generated fixture objects. Full list parsing/scoring remains the scale bottleneck; dedupe is indexed except conservative same-company/title fuzzy groups.

# 10. SUPABASE STATUS

❓ Not verified — credentials unavailable. Local PostgreSQL-engine migration/RLS/RPC tests passed; this does not prove hosted PostgREST, staging concurrency, backups, service-role configuration or hosted performance. No production migration applied.

# 11. AI STATUS

❓ Not configured. Deterministic extraction works; structured validation/fallback/cache tests use fixtures. No live model quality claim. Candidate profiles/resumes are not sent to a model by current classification code. Numerical ranking is deterministic.

# 12. CAN I ACTUALLY USE THE PRODUCT NOW?

Yes for personal local exploration of real public internship leads and saved/application tracking. Actual UI contains 59 current-looking leads, and four sampled application pages corresponded. No for a proven daily stream of highly suitable paid remote frontend internships from India: zero strong results for the evaluated persona, only one explicit India listing, unknown pay common. Paid discovery can expose 15 source-pay-evidence leads but seven rely on community data. Review employer requirements before applying.

Daily automation is not installed. Production, hosted Supabase, live AI and multi-user operation are not certified. The app is running locally at http://127.0.0.1:3000 during handoff; availability depends on the local processes.

# 13. REMAINING BLOCKERS

- P1: India-compatible frontend/paid/remote supply and thin tracker requirements; provider success alone does not make a useful shortlist.
- P1: Longitudinal discovery evidence; daily unique useful volume remains unknown, season defaults require operator maintenance.
- P1 before hosted launch: staging Supabase credentials, migration/repository/concurrency/backup test and owner-scoped authentication/data.
- P2 before large collections: SQL stable filters/keyset pagination, profile/version score materialization, retention and cache expiry. Ten-thousand-job full ranking is already about 1.7 seconds.
- P2: Alternative skill groups, education/geography taxonomy and calibrated labeled recommendation evaluation.
- P2 before public uploads: stronger parser sandbox, upload concurrency limits and deployment security review.
- Optional only: configured model benchmark; do not make AI mandatory to address missing live supply.

# 14. FILES CHANGED

Backend models/config/main; pipeline geography, trust, normalizer, eligibility, scoring, lifecycle, filters, dedupe and runner; public provider adapters/shared table parser; repositories/exporter/new resume parser; CLI live verification, discovery and benchmark scripts; API/reliability tests and fixture server.

Frontend job/filter/profile/platform/source views and API types; browser, migration and new smoke scripts. Supabase V3 migration. README, ARCHITECTURE, CURRENT_STATUS, this report, .env.example/.gitignore and CI workflow. Historical audits and private data are not rewritten or committed.

# 15. DATABASE MIGRATIONS

Existing V2 migration remains unchanged. New CLI-created `20261003202926_internship_reliability_v3.sql` is additive and locally repeat-tested:

- Typed listing trust/risk/completeness/fit/stipend-max/type/open-state fields and safe-recommendation index.
- Updated priority/run-state constraints preserve legacy values while accepting truthful V3 states.
- URL index is no longer globally unique; generic careers pages cannot force unrelated listings together. Provider ID/source-instance identities remain available.
- Source-instance table keyed provider+provider_job_id, job FK, canonical URL, tracker and requisition metadata; RLS and service-only access.
- Ingestion trigger keeps typed ranking columns consistent with incoming evidence JSON; reads prefer typed values. Existing intelligence is non-destructively synchronized.
- Upsert still preserves personal tracker state, and now uses typed status/favorite/hidden/notes when JSON disagrees and refreshes supplied company website/LinkedIn.
- Owner/expiry acquisition/release RPCs; completion RPC wraps jobs, raw payloads and running->final state in one transaction. Failure rolls back.

Before Phase 2/hosted use: staged migration/restore, tenant ownership columns and RLS, authoritative per-profile score versions, SQL filter/pagination, hosted retention/observability. Existing unused skills/tags/trust-history tables are preserved for compatibility, not claimed as functioning product features. DB enabled flags are explicitly legacy metadata; environment runtime enablement is the authority.

# 16. COMMITS

Implementation commits, all after passing final checks:

- `d3ea3ed` fix: harden internship safety, ranking and discovery persistence
- `9f10ad0` fix: make internship search and ranking uncertainty visible
- `acb2881` test: add reliability regressions and end-to-end product verification

The documentation close-out commit containing this report is identified in the final handoff and Git history (a commit cannot embed its own hash). Author: Ocean Kumar, approved email `67411162+oceankumar@users.noreply.github.com`. New commit attribution is checked on GitHub after push. Existing older unlinked commits are not rewritten; the Contributors page may depend on default-branch inclusion and GitHub processing. No merge to main is authorized or performed.

# 17. NEXT 5 PRIORITIES

1. Add operator-approved India-compatible internship sources and bounded employer detail enrichment for useful tracker leads.
2. Install a deployment-appropriate scheduled discovery call only after choosing hosting; measure seven-day unique active/paid/India-compatible yield and failures.
3. Verify Supabase in staging, back up/import explicitly, test concurrent tracking/discovery and restore before hosted launch.
4. Add labeled requirement alternatives and geography/degree evaluation; distinguish promising exploratory roles from unknown fit without manufacturing strong recommendations.
5. Move stable filtering/pagination and versioned ranking to SQL with retention/monitoring before large or multi-user use.
