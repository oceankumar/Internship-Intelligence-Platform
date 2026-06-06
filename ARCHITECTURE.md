# Technical Architecture: Internship Intelligence Platform

This document provides an in-depth explanation of the codebase structure, engineering design choices, and data flows within the Internship Intelligence Platform.

---

## 1. Directory Structure

```
.
├── backend
│   ├── app
│   │   ├── config.py           # Canonical absolute path resolver and settings
│   │   ├── main.py             # FastAPI entrypoint and dependency injection
│   │   ├── models.py           # Pydantic schemas, enums, migration validators
│   │   ├── pipeline
│   │   │   ├── dedupe.py       # Canonical string helpers and title matchers
│   │   │   ├── filters.py      # Regex word boundary and seniority gating
│   │   │   ├── normalizer.py   # Ingestion object standardizer
│   │   │   ├── runner.py       # Discovery runner, metrics, and logs
│   │   │   ├── scorer.py       # Ocean Kumar rule scoring engine
│   │   │   └── trust.py        # Trust score calculator and blacklist check
│   │   ├── profile.py          # Profile preferences and exclude terms
│   │   ├── providers
│   │   │   ├── base.py         # Abstract base class for search crawlers
│   │   │   ├── registry.py     # Source mapping and selection factory
│   │   │   ├── simplify_jobs.py# Community README tracker html parser
│   │   │   ├── github_jobs.py  # Markdown lists scraper
│   │   │   ├── public_datasets.py# Mentorship program YAML/JSON loader
│   │   │   ├── startup_career_pages.py# Greenhouse corporate API client
│   │   │   └── yc_jobs.py      # YC profile JSON-LD extractor
│   │   └── services
│   │       ├── exporter.py     # Dict-to-CSV / OpenPyXL excel generator
│   │       └── repository.py   # JSON read/write & Supabase Postgres integration
│   ├── requirements.txt
│   └── tests
│       └── test_pipeline.py    # Pytest unit tests suite
├── frontend
│   ├── app
│   │   ├── page.tsx            # Main dashboard, metrics hook, accordion
│   │   └── globals.css         # Styling system
│   ├── lib
│   │   └── api.ts              # API fetch types and functions
│   └── package.json
└── supabase
    └── schema.sql              # Supabase PostgreSQL schema
```

---

## 2. Ingestion & Provider Pipeline

All discovery scrapers subclass `Provider` in `base.py` and implement the abstract `discover` method. The pipeline flow is as follows:

```
[DiscoveryRequest] ➔ [Runner] ➔ Concurrency Factory (asyncio.gather)
                                            │
               ┌────────────────────────────┼────────────────────────────┐
               ▼                            ▼                            ▼
      [YC Jobs profile]             [Simplify README]            [Greenhouse API]
               │                            │                            │
               └────────────────────────────┼────────────────────────────┘
                                            │ (List of RawInternship objects)
                                            ▼
                                     [Normalizer]
                                            │ (Standardized Job object)
                                            ▼
                                     [Candidate Filter] (filters.py)
                                            │ (Gated Seniority & Word Boundary)
                                            ▼
                                     [Trust Scorer] (trust.py)
                                            │ (Evaluates Company Signals)
                                            ▼
                                     [Match Scorer] (scorer.py)
                                            │ (Ocean Kumar Weights)
                                            ▼
                                     [Repository Upsert] (repository.py)
                                            │ (Deduplication Merge & Write)
                                            ▼
                                     [Database File / Supabase]
```

### Ingestion Highlights
* **Registry Factory**: In `registry.py`, providers are registered via `SourceName` enums. The runner creates only the selected providers, enabling precise scans.
* **JSON-LD Schema Extraction**: The YC crawler searches for `<script type="application/ld+json">` inside startup company profiles. This retrieves structured `JobPosting` data containing exact wages (`baseSalary`), start dates, locations, and company URLs.

---

## 3. Candidate Filtering & Seniority Exclusions

To avoid false positive substring matches (such as `"Internal Tools"` matching `"intern"`), `filters.py` enforces regex boundary constraints:

* **Seniority Exclusions (Gated First)**: Checks the title against `\b(senior|staff|principal|lead|manager|director|vp|exec|architect|chief|lead-|sr-|sr\.)\b`. If a match is found, the job is immediately rejected, ensuring a role like `"International Lead"` is not parsed.
* **Word Boundaries**: The title must match `\b(intern|internship|co-op|coop|fellow|apprentice|student)\b`. Words like `"internal"` or `"international"` do not match because they lack a word boundary after `"intern"`.
* **Description Fallback**: If the title contains no internship or seniority keywords, the system fallbacks to the description, searching for high-confidence phrases (e.g. `"paid internship"`, `"internship role"`).

---

## 4. Match & Trust Scoring Engines

### Match Scorer (`scorer.py`)
Computes a match score (0-100) using a transparent, rule-based algorithm (strictly avoiding LLM latency/cost):
1. **Starting Score**: Starts at `20`.
2. **React/Next.js Match**: Adds `+15` for React, `+10` for Next.js.
3. **Frontend Discipline**: Adds `+15` if Frontend/Web is in the title, or `+10` if core web skills (JavaScript, TypeScript, HTML, CSS, Tailwind) are in the text.
4. **Remote status**: Adds `+15` for Remote, `+5` for Hybrid.
5. **Paid Stipend**: Adds `+15` for paid status. Deducts `-20` for unpaid, and `-5` for unclear compensation.
6. **Startup Signals**: Adds `+10` for early stage/founder signals.
7. **Entry-level & AI interest**: Adds `+5` for undergrad/student matches, and `+5` for AI/LLM terms.
8. **Experience Penalties**: Deducts `-15` points per year of experience required above 1 year to filter out roles expecting senior engineers.

### Trust Scorer (`trust.py`)
Calculates a trust score (0-100) evaluating company legitimacy. Points are awarded for having website links (`+25`), active LinkedIn company profiles (`+15`), clear company descriptions (`+15`), and positive product/hiring text signals. Companies with trust scores $< 50$ are marked as suspicious.

---

## 5. Deduplication & Merging Engine

Deduplication occurs in `repository.py` during `upsert_jobs` using a two-tier matching strategy:

### Primary Deduplication
Matches jobs sharing identical:
* `canonical_company(company_name)`
* `canonical_title(title)`

### Secondary Deduplication (Title Similarity)
Matches jobs sharing:
* `canonical_company(company_name)`
* `canonical_domain(url)` (the same corporate website application host, e.g. `palantir.com`)
* **Keyword overlap**: Shares at least one core engineering keyword (frontend, backend, developer, engineer, software, ai, ml, design, firmware, embedded).

### Merge Properties
When a duplicate is found, it is merged into the existing record:
1. **Time**: Retains the oldest `first_seen` date, and sets `last_seen` to `now()`.
2. **Sources**: Appends the new platform to the `sources[]` list and increments `source_count`.
3. **Trust**: Retains the highest `trust_score`.
4. **Stipend**: Retains the richest compensation details (prefers structured monetary ranges over default `"Paid stipend"`).
5. **Description**: Retains the longer description text.

---

## 6. Next.js Frontend Dashboard

The frontend is built on Next.js, displaying an interactive dashboard:
* **Metrics Visualization**: Shows Total Internships, New Today (`is_new`), New This Week (`days_since_seen <= 7`), Updated This Week (`source_count > 1`), Top Matches (`match_score >= 85`), High Priority count (`Apply Today`), Avg Stipend, and Flagged counts.
* **Expanded Job Row Accordion**: Triggers local React state updates to render explanation lists, matching and missing skills arrays, and source history without page refreshes.
* **Export Streaming**: Directly links button triggers to FastAPI `/api/export.csv` and `/api/export.xlsx` download streams.
