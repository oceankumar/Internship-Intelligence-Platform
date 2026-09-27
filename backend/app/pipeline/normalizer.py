import re
from html import unescape

from bs4 import BeautifulSoup

from app.models import Company, CompensationStatus, Job, RawInternship, RemoteStatus
from app.pipeline.dedupe import canonical_company, canonical_title, canonical_domain, canonical_url

SKILL_ALIASES = {
    "react": ["react", "react.js", "reactjs"],
    "next.js": ["next.js", "nextjs", "next js"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "node.js": ["node.js", "nodejs", "node js", "node"],
    "mongodb": ["mongodb", "mongo"],
    "api": ["api", "apis", "rest", "graphql"],
    "html": ["html"],
    "css": ["css", "tailwind", "sass"],
    "python": ["python"],
    "fastapi": ["fastapi"],
    "docker": ["docker"],
    "aws": ["aws", "amazon web services"],
    "postgresql": ["postgresql", "postgres"],
    "java": ["java"],
    "git": ["git", "github"],
    "figma": ["figma"],
    "pytorch": ["pytorch"],
    "sql": ["sql"],
}


def normalize_job(raw: RawInternship) -> Job:
    title = clean_title(raw.title)
    description = clean_description(raw.description)
    text = f"{title} {description}".lower()
    skills = extract_skills(text)
    company = Company(
        name=clean_company_name(raw.company_name),
        website_url=raw.company_website,
        linkedin_url=raw.company_linkedin_url,
        description=raw.company_description,
    )
    job = Job(
        company=company,
        title=title,
        url=canonical_url(raw.url),
        description=description,
        required_skills=skills,
        preferred_skills=[],
        location=normalize_location(raw.location),
        remote_status=normalize_remote_status(raw.remote_status, raw.location, raw.description),
        compensation=raw.compensation,
        compensation_status=normalize_compensation(raw.compensation, description),
        source=raw.source,
        source_id=raw.source_id,
        date_posted=raw.date_posted,
        deadline=raw.deadline,
        tags=derive_tags(text),
    )
    job.original_urls = [raw.url]
    job.provenance = {"description": {"source": raw.source.value}, "compensation": {"source": raw.source.value, "evidence": raw.compensation}}
    if raw.source.value == "public_datasets":
        job.provenance["listing_kind"] = "program_catalog"
        job.summary = "Program catalog entry; current application window is not verified."
    return enrich_fields(job)


def extract_skills(text: str) -> list[str]:
    found: list[str] = []
    for canonical, aliases in SKILL_ALIASES.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases):
            found.append(canonical)
    return found


def normalize_compensation(compensation: str | None, description: str) -> CompensationStatus:
    haystack = f"{compensation or ''} {description}".lower()
    if re.search(r"\b(unpaid|no stipend|volunteer|equity.only)\b", haystack):
        return CompensationStatus.unpaid
    if re.search(r"\bpaid (?:internship|intern|role|position|stipend)\b|\b(?:stipend|salary) (?:of|is)\s*\d|(?:[$₹]|\b(?:INR|USD|EUR|GBP|Rs\.?))\s*[1-9][\d,]*(?:\.\d+)?|[1-9][\d,]*\s*(?:INR|USD|EUR|GBP)\b", haystack, re.I):
        return CompensationStatus.paid
    return CompensationStatus.unknown


def normalize_remote_status(status: RemoteStatus, location: str | None, description: str) -> RemoteStatus:
    haystack = f"{location or ''} {description}".lower()
    if "hybrid" in haystack:
        return RemoteStatus.hybrid
    if re.search(r"\b(no remote|not remote|onsite|on-site)\b", haystack):
        return RemoteStatus.onsite
    if "remote" in haystack or status == RemoteStatus.remote:
        return RemoteStatus.remote
    return status


def normalize_location(location: str | None) -> str | None:
    if not location:
        return None
    return " ".join(location.split())


def clean_title(title: str) -> str:
    return unescape(" ".join(title.split()))[:180]


def clean_description(description: str) -> str:
    if not description:
        return ""
    text = BeautifulSoup(description, "html.parser").get_text(" ", strip=True)
    return unescape(" ".join(text.split()))


def clean_company_name(name: str) -> str:
    return " ".join(name.split()).strip()[:160] or "Unknown company"


def derive_tags(text: str) -> list[str]:
    tags: list[str] = []
    if "intern" in text:
        tags.append("internship")
    if "startup" in text or "founder" in text:
        tags.append("startup")
    if "remote" in text:
        tags.append("remote")
    if re.search(r"\b(ai|machine learning|llm)\b", text):
        tags.append("ai")
    return tags


def role_family(title: str) -> str:
    for family, pattern in [
        ("frontend", r"front.?end|react|next\.?js|web develop"),
        ("full-stack", r"full.?stack|product engineer"),
        ("backend", r"back.?end"), ("AI/ML", r"\b(ai|ml|machine learning|llm)\b"),
        ("data science", r"data scien"), ("data engineering", r"data engineer"),
        ("design", r"design|\bux\b"), ("DevOps", r"devops|infrastructure"),
        ("cybersecurity", r"security"), ("research", r"research"),
        ("product", r"product"), ("software engineering", r"software|\bswe\b|developer"),
    ]:
        if re.search(pattern, title, re.I):
            return family
    return "other"


def parse_salary(value: str | None) -> dict:
    if not value:
        return {}
    currency = next((c for c, pat in [("INR", r"₹|\bINR\b|\bRs\.?"), ("USD", r"\bUSD\b|\$"), ("EUR", r"EUR|€"), ("GBP", r"GBP|£")] if re.search(pat, value, re.I)), None)
    if not currency:
        return {}
    nums = re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*(k)?", value, re.I)
    amounts = [float(n.replace(",", "")) * (1000 if k else 1) for n, k in nums[:2]]
    if not amounts:
        return {}
    period = next((p for p, pat in [("month", r"month|/mo\b"), ("year", r"year|annual|/yr\b"), ("hour", r"hour|/hr\b"), ("week", r"week|/wk\b")] if re.search(pat, value, re.I)), None)
    return {"stipend_min": min(amounts), "stipend_max": max(amounts), "compensation_currency": currency, "compensation_period": period}


def experience_months(text: str) -> int | None:
    pattern = r"\b(\d+)(?:\s*[-–]\s*\d+)?\+?\s*(years?|yrs?|months?)\s+(?:of\s+)?(?:professional\s+|relevant\s+|work\s+)?experience"
    values = [int(n) * (1 if unit.startswith("month") else 12) for n, unit in re.findall(pattern, text, re.I)]
    return max(values) if values else None


def enrich_fields(job: Job) -> Job:
    job.normalized_title = canonical_title(job.title)
    job.normalized_company = canonical_company(job.company.name)
    job.company_domain = canonical_domain(job.company.website_url) or None
    job.role_family = role_family(job.title)
    job.minimum_experience_months = experience_months(job.description)
    from app.pipeline.filters import is_phase_one_candidate
    job.internship = is_phase_one_candidate(job)
    job.summary = job.description[:300].rsplit(" ", 1)[0] if len(job.description) > 300 else job.description
    if job.provenance.get("listing_kind") == "program_catalog":
        job.summary = "Program catalog entry; current application window is not verified. " + job.summary[:220]
    loc = job.location or ""
    job.country = next((c for c, pat in [("India", r"\bindia\b|\bIN\b|bengaluru|bangalore|mumbai|delhi"), ("United States", r"\bUS\b|\bUSA\b|united states"), ("United Kingdom", r"\bUK\b|united kingdom|london")] if re.search(pat, loc, re.I)), None)
    grad = re.search(r"graduat\w*[^.\n]{0,60}?(20\d{2})(?:\s*[-–]\s*(20\d{2}))?", job.description, re.I)
    if grad:
        first, last = int(grad[1]), int(grad[2] or grad[1])
        job.graduation_years = list(range(first, min(last, first + 8) + 1))
    for key, value in parse_salary(job.compensation).items():
        setattr(job, key, value)
    return job
