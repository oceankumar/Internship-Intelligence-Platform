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
    "node.js": ["node.js", "nodejs", "node js"],
    "mongodb": ["mongodb", "mongo"],
    "api": ["api", "apis", "rest", "graphql"],
    "html": ["html"],
    "css": ["css", "cascading style sheets"],
    "tailwind": ["tailwind", "tailwindcss"],
    "sass": ["sass", "scss"],
    "python": ["python"],
    "fastapi": ["fastapi"],
    "docker": ["docker"],
    "aws": ["aws", "amazon web services"],
    "postgresql": ["postgresql", "postgres"],
    "java": ["java"],
    "git": ["git"],
    "figma": ["figma"],
    "pytorch": ["pytorch"],
    "sql": ["sql"],
    "vue": ["vue", "vue.js", "vuejs"],
    "angular": ["angular"],
    "accessibility": ["accessibility", "a11y"],
    "jest": ["jest"], "vitest": ["vitest"],
    "cypress": ["cypress"], "playwright": ["playwright"],
    "flask": ["flask"], "django": ["django"],
    "express": ["express.js", "expressjs", "express framework"],
    "spring": ["spring boot", "spring framework"],
    "numpy": ["numpy"], "pandas": ["pandas"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "tensorflow": ["tensorflow"], "llm": ["llm", "large language models"],
    "rag": ["retrieval augmented generation", "retrieval-augmented generation", "rag"],
    "embeddings": ["embeddings"], "kubernetes": ["kubernetes", "k8s"],
    "azure": ["azure"], "gcp": ["gcp", "google cloud"],
}


def normalize_job(raw: RawInternship) -> Job:
    title = clean_title(raw.title)
    description = clean_description(raw.description)
    text = f"{title} {description}".lower()
    required, preferred, mentioned = classify_skills(description)
    company = Company(
        name=clean_company_name(raw.company_name),
        website_url=raw.company_website,
        linkedin_url=raw.company_linkedin_url,
        description=raw.company_description,
    )
    compensation = raw.compensation or extract_compensation(description)
    job = Job(
        company=company,
        title=title,
        url=canonical_url(raw.url),
        description=description,
        required_skills=required,
        preferred_skills=preferred,
        mentioned_skills=sorted(set(mentioned + extract_skills(title.lower()))),
        location=normalize_location(raw.location),
        remote_status=normalize_remote_status(raw.remote_status, raw.location, raw.description),
        compensation=compensation,
        compensation_status=normalize_compensation(compensation, description),
        source=raw.source,
        source_id=raw.source_id,
        date_posted=raw.date_posted,
        deadline=raw.deadline,
        tags=derive_tags(text),
    )
    job.original_urls = [raw.url]
    from app.pipeline.dedupe import specific_url
    if job.source_id and job.source_id.startswith(('http://','https://')) and canonical_url(job.source_id) == job.url and not specific_url(job.url):
        job.source_id = None
    job.provenance = {"description": {"source": raw.source.value}, "compensation": {"source": raw.source.value, "evidence": raw.compensation}}
    job.provenance["source_values"] = {"remote_status": job.remote_status.value, "compensation_status": job.compensation_status.value, "required_skills": required}
    job.source_instances = [{"provider": raw.source.value, "provider_job_id": job.source_id or "", "canonical_apply_url": job.url, "tracker_url": str(raw.raw.get("tracker_url", "")), "requisition_id": str(raw.raw.get("requisition_id") or "")}]
    from app.pipeline.dedupe import identity_keys
    requisition = next((key.split(':', 1)[1] for key in identity_keys(job) if key.startswith('greenhouse:')), '')
    if requisition:
        job.source_instances[0]['requisition_id'] = requisition
    if raw.raw.get("employment_type") == "internship":
        job.provenance["explicit_internship"] = True
    job.application_state = "closed" if raw.raw.get("closed") else "open" if raw.raw.get("application_state") == "open" else "unknown"
    if raw.source.value == "public_datasets":
        job.provenance["listing_kind"] = "program_catalog"
        job.opportunity_type = "open_source_program"
        job.summary = "Program catalog entry; current application window is not verified."
    return enrich_fields(job)


def extract_skills(text: str) -> list[str]:
    text = text.lower()
    found: list[str] = []
    for canonical, aliases in SKILL_ALIASES.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases):
            found.append(canonical)
    return found


def classify_skills(description: str) -> tuple[list[str], list[str], list[str]]:
    required, preferred = set(), set()
    scope = "mentioned"
    for line in re.split(r"\n|;|(?<=[.!?])\s+", description):
        lower = line.lower()
        heading = lower.strip().strip(':')
        if re.search(r"^(?:minimum |basic )?(?:requirements|qualifications)$|^about you$|^we.d love to hear from you", heading):
            scope = "required"
        elif re.search(r"^preferred (?:qualifications|requirements)$|^nice.to.have$", heading):
            scope = "preferred"
        elif re.search(r"^(?:what you.ll do|what you will do|responsibilities|benefits|about us|compensation|pay transparency|disclosures|at figma|equal opportunity|privacy|examples of accommodations)", heading):
            scope = "mentioned"
        if re.search(r"not required|no .{0,25}experience required|we work mostly|languages can be learned", lower):
            category = "mentioned"
        elif re.search(r"preferred|nice.to.have|bonus|a plus|optional", lower):
            category = "preferred"
        elif re.search(r"required|requirements|qualifications|must have|proficien|experience (?:with|in|coding)|knowledge (?:of|and capability with)|familiarity with|you (?:have|bring)", lower):
            category = "preferred" if scope == "preferred" and not re.search(r"must|required",lower) else "required"
        elif re.search(r"responsibilities|what you.ll do|benefits|about us|compensation", lower):
            category = "mentioned"
        else:
            category = scope
        if len(line.strip()) < 90 and (":" in line or re.search(r"^(?:minimum |preferred |basic )?(?:requirements|qualifications)|^nice.to.have", lower)):
            scope = category
        skills = set(extract_skills(lower))
        if category == "required":
            required.update(skills)
        elif category == "preferred":
            preferred.update(skills)
    return sorted(required), sorted(preferred - required), extract_skills(description)


def normalize_compensation(compensation: str | None, description: str) -> CompensationStatus:
    haystack = f"{compensation or ''} {extract_compensation(description) or ''} {description if re.search(r'\bpaid (?:internship|intern|role|position)\b', description, re.I) else ''}".lower()
    if re.search(r"\b(unpaid|no stipend|volunteer|equity.only)\b", description, re.I):
        return CompensationStatus.unpaid
    if re.search(r"\b(unpaid|no stipend|volunteer|equity.only)\b", haystack):
        return CompensationStatus.unpaid
    if re.search(r"\bpaid (?:internship|intern|role|position|stipend)\b|\b(?:stipend|salary) (?:of|is)\s*\d|(?:[$₹]|\b(?:INR|USD|EUR|GBP|Rs\.?))\s*[1-9][\d,]*(?:\.\d+)?|[1-9][\d,]*\s*(?:INR|USD|EUR|GBP)\b", haystack, re.I):
        return CompensationStatus.paid
    return CompensationStatus.unknown


def extract_compensation(description: str) -> str | None:
    for line in re.split(r"\n|(?<=[.!?])\s+", description):
        if re.search(r"salary|stipend|compensation|pay range|hourly rate|wages?", line, re.I) and re.search(r"(?:[$\u20b9\u20ac\u00a3]|\b(?:USD|INR|EUR|GBP))\s*\d", line):
            amount = re.search(r"(?:[$\u20b9\u20ac\u00a3]|\b(?:USD|INR|EUR|GBP))\s*\d[\d,.]*(?:\s*k)?(?:\s*[-\u2013]\s*(?:[$\u20b9\u20ac\u00a3]|USD|INR|EUR|GBP)?\s*\d[\d,.]*(?:\s*k)?)?[^.\n]{0,25}", line, re.I)
            return amount[0] if amount else None
    return None


def normalize_remote_status(status: RemoteStatus, location: str | None, description: str) -> RemoteStatus:
    haystack = f"{location or ''} {description}".lower()
    if "hybrid" in (location or '').lower() or re.search(r"(?:this|the) (?:role|position|internship).{0,50}hybrid|hybrid (?:role|position|internship)", haystack):
        return RemoteStatus.hybrid
    if re.search(r"\b(no remote|not remote|onsite|on-site)\b", haystack):
        return RemoteStatus.onsite
    if "remote" in (location or '').lower() or re.search(r"(?:this|the) (?:role|position|internship).{0,60}\bremote\b|\bremote (?:role|position|internship)\b|\bfully remote\b|\bwork(?:ing)? (?:fully )?remotely\b", haystack) or status == RemoteStatus.remote:
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
    text = BeautifulSoup(unescape(description), "html.parser").get_text("\n", strip=True)
    return "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())


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
        job.opportunity_type = "open_source_program"
        job.summary = "Program catalog entry; current application window is not verified. " + job.summary[:220]
    loc = job.location or ""
    from app.pipeline.geography import extract_geography
    extract_geography(job)
    job.mentioned_skills = sorted(set(job.mentioned_skills + extract_skills(job.description)))
    if job.provenance.get("legacy_record"):
        job.required_skills, job.preferred_skills, _ = classify_skills(job.description)
    degree = re.search(r"(?:bachelor|master|ph\.?d|b\.?tech|undergraduate)[^.\n]{0,80}(?:degree|program|computer science|engineering)|(?:degree|enrolled)[^.\n]{0,80}(?:computer science|engineering)", job.description, re.I)
    job.degree_requirement = degree[0] if degree else None
    grad = re.search(r"graduat\w*[^.\n]{0,60}?(20\d{2})(?:\s*[-–]\s*(20\d{2}))?", job.description, re.I)
    if grad:
        first, last = int(grad[1]), int(grad[2] or grad[1])
        job.graduation_years = list(range(first, min(last, first + 8) + 1))
    for key, value in parse_salary(job.compensation).items():
        setattr(job, key, value)
    return job
