from urllib.parse import urlparse

from app.models import Company, Job

BLACKLIST_COMPANIES = {
    "unified mentor",
    "wake up whistle",
    "bharat intern",
    "internpe",
}


def score_company_trust(company: Company, job: Job | None = None) -> Company:
    name_lower = company.name.lower()
    if any(blacklisted in name_lower for blacklisted in BLACKLIST_COMPANIES):
        company.trust_score = 0
        company.suspicious = True
        company.excluded = True
        company.trust_reasons = ["Company is on the blacklist"]
        return company

    score = 20
    reasons: list[str] = []

    if company.website_url and _looks_like_url(company.website_url):
        score += 25
        reasons.append("Company website present")
    else:
        reasons.append("Missing company website")

    if company.linkedin_url and "linkedin.com" in company.linkedin_url:
        score += 15
        reasons.append("LinkedIn company page present")
    else:
        reasons.append("LinkedIn company page missing")

    description = company.description or ""
    if len(description.split()) >= 20:
        score += 15
        reasons.append("Meaningful company description")
    else:
        reasons.append("Thin company description")

    if job:
        job_text = f"{job.title} {job.description}".lower()
        if any(term in job_text for term in ["product", "customers", "users", "platform", "api", "app"]):
            score += 15
            reasons.append("Product or customer signal")
        else:
            reasons.append("Weak product signal")
        if any(term in job_text for term in ["founder", "team", "engineer", "employees", "hiring"]):
            score += 10
            reasons.append("Team or employee signal")
        else:
            reasons.append("Weak employee signal")

    company.trust_score = max(0, min(100, score))
    company.suspicious = company.trust_score < 50
    company.trust_reasons = reasons
    return company


def apply_trust(job: Job) -> Job:
    job.company = score_company_trust(job.company, job)
    job.suspicious = job.company.suspicious
    return job


def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme in {"http", "https"} and parsed.netloc)

