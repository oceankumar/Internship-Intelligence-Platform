# InternAI - Internship Intelligence Platform

## One-Line Version
Full-stack internship intelligence platform with multi-source ingestion, explainable ranking, eligibility and listing-risk analysis, and application tracking.

## 2-Bullet Resume Version
- Built InternAI with Next.js and FastAPI, aggregating public internship sources into a searchable discovery and tracking workflow.
- Engineered normalization, conservative deduplication and explainable eligibility/risk-aware ranking, backed by 112 backend tests and automated migration/browser checks.

## Best 3 Resume Bullets
- Built a full-stack internship intelligence platform with Next.js, TypeScript and FastAPI, supporting multi-source ingestion, search, filters and application tracking.
- Engineered metadata normalization, requisition-aware deduplication, eligibility checks and listing-risk quarantine with deterministic, explainable candidate ranking.
- Implemented PostgreSQL/Supabase adapters, CSV/XLSX exports and automated API, migration and desktop/mobile workflow tests through GitHub Actions.

## 4-Bullet Technical Version
- Built a responsive Next.js/React interface and FastAPI REST backend for internship discovery, profile matching and tracking.
- Integrated six enabled public-source types with bounded requests, independent failures, throttling, caching and discovery leases.
- Normalized inconsistent metadata and deduplicated source/URL/requisition identities while preserving tracking state and explaining skill/geography/eligibility constraints.
- Added 112 backend tests, PostgreSQL-engine migration/RLS/RPC checks and Playwright private/demo workflows with a read-only Vercel Services configuration.

After production verification is recorded in CURRENT_STATUS, the fourth bullet may read: "Deployed Next.js and FastAPI as Vercel Services with a private backend binding and a sanitized read-only recruiter demo." Do not append scheduled discovery or hosted persistence without evidence.

## Tech Stack
Next.js, React, TypeScript, Python, FastAPI, Pydantic, PostgreSQL, Supabase, REST APIs, GitHub Actions, Playwright, Pytest, Vercel Services.

## Links
- GitHub: https://github.com/oceankumar/Internship-Intelligence-Platform
- Demo: https://internai-oceankumars-projects.vercel.app
- Evidence: [CURRENT_STATUS](CURRENT_STATUS.md)

## Verified Metrics
- 112 backend tests; reproduced baseline was 95.
- Six enabled source types; two disabled restricted/overlapping adapters. Catalogs are not active inventory.
- October 5 IST probe: 68 candidates, 67 accepted including seven catalogs, 66 unique records, 59 active-looking leads, 15 pay-evidence records, two remote, one explicitly India-compatible.
- CSV and XLSX export; 1440px desktop and 390px mobile checks.

Individual and combined probes reuse cached responses; this is one bounded sample, not daily independent measurements. Prior synthetic 10,000-job benchmark remains historical, not production latency or a newly reproduced metric.

## Claims To Avoid
No daily supply, accuracy percentages, users, hiring outcomes, autonomous applications, multi-user SaaS or hosted persistence without evidence. Ranking is deterministic, not LLM-generated. Unpaid and experience-mismatched leads are often ranked lower, not universally rejected. Pay evidence is not independently confirmed payment.

Optional classification is implemented, schema validated, evidence checked and fixture tested with caching/fallback. No production model is configured. ContextIQ remains the RAG project; InternAI demonstrates full-stack and data engineering.

## Interview Talking Points

### Why Build It?
Public listings are inconsistent and rarely reflect candidate constraints. Unified discovery/tracking makes those gaps explicit instead of hiding them behind a score.

### Why FastAPI? Why Next.js?
FastAPI provides typed Python REST boundaries around ingestion/scoring. Next.js provides responsive React views and a server-side same-origin proxy that keeps credentials off the browser.

### Why PostgreSQL/Supabase?
Relational identities, constraints, indexes, RLS and transactional completion fit job/provider/tracking data. Local JSON is development-only, not writable serverless production storage.

### How Does Deduplication Avoid False Merges?
Source IDs, canonical URLs and employer requisitions take precedence. Generic application URLs are not identities; distinct ATS requisitions stay separate. Richer evidence merges conservatively and personal tracking survives updates.

### How Does Matching Work?
Weights: skills 40, role 25, experience 15, remote 10, compensation 10. Fit and completeness are separate. Unknown requirements earn no arbitrary fit; skill coverage, geographic conflicts and ineligibility constrain recommendations.

### Why Deterministic Ranking? How Is AI Used?
Explicit weights are auditable and reproducible. Optional validated LLM output classifies description evidence; it cannot fabricate scores or silently replace deterministic facts.

### Incomplete Descriptions And Suspicious Listings?
Unknown skills/pay/location remain uncertain and reduce confidence. Listing-level fee/messaging/scam signals are separate from company identity; negation handling reduces false positives and high-risk listings are quarantined.

### Geography And Eligibility?
Country, remote region, education, graduation and experience inform conflicts/uncertainty. Remote does not mean worldwide; visa and relocation are not inferred.

### Provider Failure And Rate Limits?
Independent source reports, concurrency caps, per-host intervals, bounded retry/timeouts and caches isolate failures. Internal limits are not official quotas or permission for restricted scraping.

### Production And Demo Safety?
One Vercel Services project publicly routes only Next.js. A private binding plus token authorizes backend calls. Demo reads sanitized public data and rejects writes at both layers; no private files are loaded.

### What Changes At 10x Traffic?
SQL filters/keyset pagination, versioned profile score materialization, bounded caches, retention and observability. Owner-scoped auth/RLS precede multi-user use; hosted transactions and failure recovery precede a production scheduler.
