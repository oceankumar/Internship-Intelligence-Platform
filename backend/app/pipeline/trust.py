import re
from urllib.parse import urlsplit

from app.config import get_settings
from app.models import Company, Job
from app.pipeline.dedupe import canonical_domain, canonical_company
from app.pipeline.urls import safe_public_url

ATS = {"boards.greenhouse.io", "job-boards.greenhouse.io", "jobs.lever.co", "jobs.ashbyhq.com"}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "shorturl.at"}


def score_company_trust(company: Company, job: Job | None = None) -> Company:
    settings = get_settings()
    domain = canonical_domain(job.url if job else company.website_url)
    reasons = ["Baseline evidence score (+30)"]
    score = 30
    if company.excluded or canonical_company(company.name) in {canonical_company(n) for n in settings.blocked_companies} or any(domain == d or domain.endswith('.' + d) for d in settings.blocked_domains):
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
    if company.name and "unknown" not in company.name.lower() and company.name not in {"YC company", "Startup company", "Wellfound company"}:
        score += 5
        reasons.append("Named company (+5)")
    company.trust_score = max(0, min(100, score))
    company.suspicious = False
    company.trust_reasons = reasons
    return company


def risk_signals(text: str) -> list[str]:
    reasons = []
    for sentence in re.split(r"[.!?;\n]|\b(?:but|however)\b", text, flags=re.I):
        benign_fee = re.search(r"(?:no|without|never|not|don't|do not)\s+(?:\w+\s+){0,4}(?:fee|fees|charge|charges|pay|payment|deposit)|(?:fee|payment).{0,20}(?:not required|waived)", sentence, re.I)
        fee = re.search(r"(?:pay|payment|deposit|fee|charge).{0,70}(?:apply|application|registration|join|hiring|secure|before)|(?:application|registration|recruitment|joining)\s+(?:fee|deposit)|(?:apply|join|hiring).{0,35}(?:fee|deposit|payment)", sentence, re.I)
        if fee and not benign_fee:
            reasons.append("Payment/fee requested from candidates")
        if re.search(r"(?:whatsapp|telegram).{0,40}\bonly\b|\bonly\b.{0,40}(?:whatsapp|telegram)", sentence, re.I):
            reasons.append("Messaging-only recruitment")
        if re.search(r"guaranteed.{0,25}(?:income|earnings)", sentence, re.I):
            reasons.append("Guaranteed earnings claim")
    return list(dict.fromkeys(reasons))


def apply_trust(job: Job) -> Job:
    job.company = score_company_trust(job.company, job)
    job.risk_reasons = risk_signals(job.description)
    invalid = not safe_public_url(job.url)
    shortened = canonical_domain(job.url) in SHORTENERS
    if invalid:
        job.risk_reasons.append("Invalid or non-public application URL")
    if job.company.excluded:
        job.risk_reasons.append("Excluded by configured policy")
    job.listing_risk_score = 100 if invalid or job.company.excluded else min(100, len(job.risk_reasons) * 50 + (25 if shortened else 0))
    job.risk_state = "blocked" if invalid or job.company.excluded else "quarantined" if job.risk_reasons else "review" if shortened or job.company.trust_score < 50 else "normal"
    if shortened:
        job.risk_reasons.append("Shortened URL requires destination review")
    job.trust_score = max(0, job.company.trust_score - job.listing_risk_score)
    job.suspicious = job.risk_state in {"quarantined", "blocked"} or job.trust_score < get_settings().minimum_trust
    job.trust_level = "high" if job.trust_score >= 80 else "moderate" if job.trust_score >= 50 else "review"
    return job
