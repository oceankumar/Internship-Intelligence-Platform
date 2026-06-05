import hashlib
import re

from app.models import Job


def job_fingerprint(job: Job) -> str:
    key = f"{job.company.name}|{job.title}|{canonical_url(job.url)}".lower()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def company_fingerprint(name: str, website_url: str | None = None) -> str:
    website = canonical_domain(website_url) if website_url else ""
    key = website or re.sub(r"[^a-z0-9]+", "", name.lower())
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def canonical_url(url: str) -> str:
    return url.split("?")[0].rstrip("/")


def canonical_domain(url: str | None) -> str:
    if not url:
        return ""
    cleaned = url.replace("https://", "").replace("http://", "").split("/")[0]
    return cleaned.removeprefix("www.").lower()

