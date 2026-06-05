# Audit Report

Date: June 5, 2026

## Executive Summary

The architecture is functional but internship discovery volume is currently far below the product goal.

Current effective discovery volume is approximately 1 relevant internship.

Target discovery volume is 50-100 relevant internships per day.

The primary bottleneck is data acquisition, not application automation.

---

## Provider Audit

### RemoteOK

Status: Live

How jobs are fetched:
GET https://remoteok.com/api

Current measured volume:

* Raw feed: 95 jobs
* Last 24h internships: 0
* Usable internships: 0

Issues:

* No pagination
* No retries/backoff
* No rate limiting
* company_logo incorrectly treated as website
* Query matching too broad

---

### YC Jobs

Status: Live

How jobs are fetched:
GET https://www.ycombinator.com/jobs

Current measured volume:

* Raw jobs: 20
* Usable internships: 1

Issues:

* Parser only extracts anchor tags
* Ignores embedded structured job data
* Missing salary
* Missing location
* Missing skills
* Missing experience requirements

---

### Work at a Startup

Status: Broken

Current result:
HTTP 406

Current measured volume:
0 jobs

Issues:

* Endpoint rejects request
* Requires new extraction strategy

---

### Wellfound

Status: Blocked

Current result:
HTTP 403

Protection:
DataDome

Current measured volume:
0 jobs

Issues:

* Anti-bot protection
* Needs compliant alternative

---

## Trust Scoring Audit

Current Algorithm:

Starts at:
20

Adds:
+25 Website
+15 LinkedIn
+15 Description
+15 Product keywords
+10 Team keywords

Suspicious:
Trust Score < 50

Weaknesses:

* Does not verify websites
* Does not verify LinkedIn
* Uses keyword heuristics
* No employee validation
* No company age validation
* No funding validation
* No evidence storage

Recommended Improvements:

1. Company enrichment stage
2. Website validation
3. LinkedIn validation
4. Evidence-based scoring
5. Historical trust storage

---

## Relevance Scoring Audit

Current Logic:

Starts:
40

Adds:
+25 title match
+20 skills
+12 remote
+10 India
+18 paid
+8 startup

Subtracts:
-45 unpaid
-8 compensation unknown
-35 senior terms

Issues:

* Senior roles still score too highly
* Experience requirements not parsed
* Compensation confidence weak
* Internship detection weak

Recommended Improvements:

1. Experience parser
2. Internship-only gating
3. Compensation confidence scoring
4. Better role classification

---

## Database Audit

Current Tables:

* companies
* jobs
* job_sources
* job_skills
* trust_scores
* tags
* company_exclusions

Issues:

* Missing discovery_runs
* Missing raw_jobs
* No source health tracking
* No batch writes
* Exclusions not integrated
* Tags not populated
* Skills not populated

Recommended Improvements:

1. Add discovery_runs
2. Add raw_jobs
3. Batch Supabase writes
4. Add source observability
5. Integrate exclusions

---

## Priority Fixes

Priority 1

Fix discovery volume.

Current:
1 internship

Target:
50-100 internships/day

Priority 2

Improve YC structured data extraction.

Priority 3

Replace or repair Work at a Startup integration.

Priority 4

Handle Wellfound limitations.

Priority 5

Implement observability tables.

Priority 6

Upgrade trust scoring.

Priority 7

Upgrade relevance scoring.

---

## Conclusion

The project architecture is sound.

The current bottleneck is internship discovery volume and data quality.

No application automation should be built until discovery quality reaches at least 50 relevant internships per day.
