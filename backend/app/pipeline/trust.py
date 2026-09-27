import re
from urllib.parse import urlsplit

from app.config import get_settings
from app.models import Company, Job
from app.pipeline.dedupe import canonical_domain
from app.pipeline.urls import safe_public_url

ATS = {"boards.greenhouse.io", "job-boards.greenhouse.io", "jobs.lever.co", "jobs.ashbyhq.com"}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "shorturl.at"}


def score_company_trust(company: Company, job: Job | None = None) -> Company:
    settings = get_settings()
    domain = canonical_domain(job.url if job else company.website_url)
    reasons = ["Baseline evidence score (+30)"]
    score = 30
    if company.excluded or company.name.casefold().strip() in settings.blocked_companies or domain in settings.blocked_domains:
        company.trust_score, company.suspicious, company.excluded = 0, True, True
        company.trust_reasons = ["Excluded by configured company/domain policy"]
        return company
    url = job.url if job else company.website_url or ""
    if not safe_public_url(url):
        score -= 30
        reasons.append("Invalid or non-public application URL (-30)")
    elif urlsplit(url).scheme == "https":
        score += 10
        reasons.append("HTTPS application link (+10); identity not independently verified")
    if domain in ATS or domain.endswith(".myworkdayjobs.com"):
        score += 25
        reasons.append("Recognized ATS hostname (+25)")
    if domain in {"ycombinator.com", "remoteok.com"}:
        score += 20
        reasons.append("Known public job board (+20)")
    if company.website_url and canonical_domain(company.website_url) == domain:
        score += 15
        reasons.append("Application and supplied company domain agree (+15)")
    if job and len(job.description.split()) >= 80:
        score += 15
        reasons.append("Substantial description (+15)")
    if company.name and "unknown" not in company.name.lower() and company.name not in {"YC company", "Startup company", "Wellfound company"}:
        score += 5
        reasons.append("Named company (+5)")
    if domain in SHORTENERS:
        score -= 25
        reasons.append("Shortened application URL obscures destination (-25)")
    text = job.description if job else ""
    for pattern, penalty, label in [
        (r"(?:pay|payment|fee|deposit).{0,35}(?:to apply|registration|secure.{0,10}(?:role|internship))", 65, "Payment requested to apply"),
        (r"(?:whatsapp|telegram).{0,25}only|only.{0,25}(?:whatsapp|telegram)", 30, "Messaging-only recruitment"),
        (r"guaranteed.{0,20}(?:income|earnings)", 25, "Guaranteed earnings claim"),
    ]:
        if re.search(pattern, text, re.I):
            score -= penalty
            reasons.append(f"{label} (-{penalty})")
    company.trust_score = max(0, min(100, score))
    company.suspicious = company.trust_score < settings.minimum_trust
    company.trust_reasons = reasons
    return company


def apply_trust(job: Job) -> Job:
    job.company = score_company_trust(job.company, job)
    job.suspicious = job.company.suspicious
    job.trust_level = "high" if job.company.trust_score >= 80 else "moderate" if job.company.trust_score >= 50 else "review"
    return job
