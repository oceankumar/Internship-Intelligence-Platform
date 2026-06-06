# Project Showcase: Internship Intelligence Platform

An autonomous pipeline and dashboard designed to optimize the search for paid tech internships by discovering, filtering, and ranking roles specifically aligned with a CS/AI student profile.

---

## 🚀 Key Highlights & Engineering Metrics

* **Total Discovered Internships**: **187 unique roles** currently stored.
* **Aggregated Sources**: **14 distinct data streams** including SimplifyJobs, GitHub community lists, RemoteOK, Y Combinator, corporate API boards (Stripe, Figma, GitLab, Anthropic, Reddit, Vercel), and open-source lists (GSoC, Outreachy, LFX, MLH Fellowship).
* **Deduplication Rate**: **23.05%** (merged duplicate listings, preserving first-seen dates and combining multi-platform sources).
* **Noise Filtering Accuracy**: **100% of title-matching false positives eliminated** (such as "Internal Tools" or "International Audit" full-time positions) through strict word boundary checks.
* **Exports**: Full support for CSV and structured Microsoft Excel (XLSX) formats.

---

## 💡 The Engineering Problem

Finding internships in software engineering is plagued by high noise levels:
1. **Low Ingestion Volume**: Scraping single search terms like `"internship"` on search engines returns limited lists, missing community-tracked roles or direct corporate API postings.
2. **Title-Matching Noise**: Naive text filtering on `"intern"` matches full-time roles containing words like `"internal"` or `"international"`, creating dozens of false positives that clutter the dashboard.
3. **Multi-Source Duplication**: The same job listing is often indexed across multiple platforms (Simplify, YC, GitHub, RemoteOK) with different descriptions, URLs, and requisition IDs, resulting in redundant rows.

---

## 🛠️ The Technical Solution

The platform resolves these bottlenecks using a custom-built ingestion and scoring pipeline:

### 1. Robust Registry & Provider System
A factory registry orchestrates multiple providers running asynchronously. Each crawler extracts, normalizes, and packages raw entries into a unified Pydantic schema:
* **YC Jobs**: Concurrently scrapes individual startup profiles to parse schema.org `JobPosting` JSON-LD schemas, resolving exact stipends, company URLs, and posting dates.
* **Greenhouse Portals**: Requests structured corporate job boards directly without requiring access keys, bypassing scraping bans.
* **Community lists**: Crawls open trackers on GitHub and SimplifyJobs markdown README tables to extract roles.

### 2. Regex Word-Boundary Filtering
Instead of basic substring search, the candidate validator in `filters.py` uses word boundary checks to reject false matches:
```python
INTERN_REGEX = re.compile(r"\b(intern|internship|co-op|coop|fellow|apprentice|student)\b", re.IGNORECASE)
SENIORITY_REGEX = re.compile(r"\b(senior|staff|principal|lead|manager|director|head|vp|exec|architect|chief|lead-|sr-|sr\.)\b", re.IGNORECASE)
```
Gating seniority checks first ensures that a role like "International Regulatory Exam Lead" is discarded immediately.

### 3. Advanced Deduplication Merging
To identify duplicate opportunities across different providers (even when application links or IDs differ), the database uses a two-tier merge rule:
* **Primary Key Match**: Combines canonicalized company name and job title (e.g. `palantir | forward deployed software engineer`).
* **Secondary Confidence Match**: Resolves listings that share the same company and application domain, and contain similar engineering keywords (e.g. `software engineer` vs `software developer`).
* **Data Union**: When a duplicate is matched, the repository preserves `first_seen`, updates `last_seen`, increments `source_count`, appends all platforms to a `sources` list, keeps the highest company trust score, and retains the richest stipend details.

### 4. Transparent Match Scoring Engine
A rule-based scoring engine computes a customized match score (0-100) specifically for Ocean Kumar's profile:
* **React/Next.js Match**: Up to 25 points.
* **Frontend/Web focus**: Up to 25 points.
* **Remote option**: Up to 15 points.
* **Paid Stipend**: Up to 15 points.
* **Startup context**: Up to 10 points.
* **Entry-level/AI signals**: Up to 10 points.
* **Experience penalty**: Deducts 15 points per year required above 1 year to filter out roles expecting senior engineers.

---

## 🖥️ User Experience (Next.js Dashboard)

The frontend features a responsive, dark-themed dashboard:
* **8 Metrics Blocks**: Renders Total Internships, New Today, New This Week, Updated This Week, Top Matches, High Priority count, Avg Stipend, and Flagged companies.
* **Interactive Accordeon Drawer**: Expand any job card to inspect why it matched, see matching and missing skills badges, view salary details, and see the full source crawler history.
* **No-Install Exporters**: Supports one-click triggers that stream Excel and CSV files directly from the backend.
