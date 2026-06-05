import re
from html import unescape

from bs4 import BeautifulSoup

from app.models import Company, CompensationStatus, Job, RawInternship, RemoteStatus

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
    return Job(
        company=company,
        title=title,
        url=raw.url,
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
        tags=derive_tags(text),
    )


def extract_skills(text: str) -> list[str]:
    found: list[str] = []
    for canonical, aliases in SKILL_ALIASES.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases):
            found.append(canonical)
    return found


def normalize_compensation(compensation: str | None, description: str) -> CompensationStatus:
    haystack = f"{compensation or ''} {description}".lower()
    if any(term in haystack for term in ["unpaid", "no stipend", "volunteer", "equity only"]):
        return CompensationStatus.unpaid
    if compensation and compensation.strip():
        return CompensationStatus.paid
    if any(term in haystack for term in ["paid", "stipend", "salary", "$", "₹", "inr", "usd"]):
        return CompensationStatus.paid
    return CompensationStatus.unknown


def normalize_remote_status(status: RemoteStatus, location: str | None, description: str) -> RemoteStatus:
    haystack = f"{location or ''} {description}".lower()
    if "remote" in haystack or status == RemoteStatus.remote:
        return RemoteStatus.remote
    if "hybrid" in haystack:
        return RemoteStatus.hybrid
    if "onsite" in haystack or "on-site" in haystack:
        return RemoteStatus.onsite
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
    if "ai" in text or "machine learning" in text or "llm" in text:
        tags.append("ai")
    return tags
