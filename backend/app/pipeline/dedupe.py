import hashlib
import re
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.models import Job


def canonical_url(url: str) -> str:
    try:
        p = urlsplit(url.strip())
        query = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith("utm_") and k.lower() not in {"ref", "source", "referral"}]
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), urlencode(sorted(query)), ""))
    except ValueError:
        return url


def canonical_domain(url: str | None) -> str:
    try:
        return (urlsplit(url or "").hostname or "").removeprefix("www.").lower()
    except ValueError:
        return ""


def canonical_company(name: str) -> str:
    name = re.sub(r"\b(incorporated|inc|corp|ltd|llc|gmbh)\.?$", "", name.lower().strip())
    return " ".join(re.sub(r"[^\w\s]", " ", name).split())


def canonical_title(title: str) -> str:
    title = title.lower()
    for pat, replacement in [(r"\bswe\b", "software engineer"), (r"\bsoftware engineering\b", "software engineer"), (r"\binternship\b", "intern"), (r"front[ -]end", "frontend"), (r"back[ -]end", "backend"), (r"full[ -]stack", "fullstack")]:
        title = re.sub(pat, replacement, title)
    return " ".join(re.sub(r"[^\w\s]", " ", title).split())


def titles_are_similar(a: str, b: str) -> bool:
    return canonical_title(a) == canonical_title(b)


def job_fingerprint(job: Job) -> str:
    return hashlib.sha256(canonical_url(job.url).encode()).hexdigest()[:24]


def company_fingerprint(name: str, website_url: str | None = None) -> str:
    return hashlib.sha256(canonical_company(name).encode()).hexdigest()[:24]


def same_job(a: Job, b: Job) -> bool:
    if {canonical_url(u) for u in [a.url, *a.original_urls]}.intersection(canonical_url(u) for u in [b.url, *b.original_urls]):
        return True
    if a.source == b.source:
        return bool(a.source_id and b.source_id and a.source_id == b.source_id)
    if canonical_company(a.company.name) != canonical_company(b.company.name):
        return False
    if canonical_title(a.title) != canonical_title(b.title):
        return False
    if not a.location or not b.location or a.location.casefold() != b.location.casefold():
        return False
    # Different requisitions can have identical titles: require corroborating text.
    return min(len(a.description), len(b.description)) >= 160 and SequenceMatcher(None, a.description, b.description).ratio() >= 0.92


USER_FIELDS = ("application_status", "applied_at", "favorite", "hidden", "notes", "interview_at", "reminder_at", "contact", "corrections")


def merge_jobs(existing: list[Job], incoming: list[Job]) -> tuple[list[Job], dict[str, int]]:
    output = [j.model_copy(deep=True) for j in existing]
    metrics = {"new": 0, "updated": 0, "duplicates": 0}
    for item in incoming:
        old = next((j for j in output if same_job(j, item)), None)
        fresh = item.model_copy(deep=True)
        fresh.id = old.id if old else (fresh.id or job_fingerprint(fresh))
        fresh.company.id = old.company.id if old else company_fingerprint(fresh.company.name)
        if old:
            metrics["duplicates"] += 1
            metrics["updated"] += 1
            if len(old.description) > len(fresh.description):
                fresh.description, fresh.summary = old.description, old.summary
                fresh.required_skills, fresh.preferred_skills = old.required_skills, old.preferred_skills
            if not fresh.compensation:
                for key in ("compensation", "compensation_status", "stipend_min", "stipend_max", "compensation_currency", "compensation_period"):
                    setattr(fresh, key, getattr(old, key))
            fresh.first_seen = old.first_seen
            fresh.date_discovered = old.date_discovered
            for key in ("date_posted", "deadline", "location"):
                if getattr(fresh, key) is None:
                    setattr(fresh, key, getattr(old, key))
            fresh.provenance = {**old.provenance, **fresh.provenance}
            if not fresh.company.website_url:
                fresh.company.website_url = old.company.website_url
            fresh.company.excluded = old.company.excluded or fresh.company.excluded
            for key in USER_FIELDS:
                setattr(fresh, key, getattr(old, key))
            fresh.sources = list(dict.fromkeys(old.sources + fresh.sources + [fresh.source]))
            fresh.original_urls = list(dict.fromkeys(old.original_urls + [old.url] + fresh.original_urls + [fresh.url]))
            fresh.url, fresh.source, fresh.source_id = old.url, old.source, old.source_id
            output[output.index(old)] = fresh
        else:
            metrics["new"] += 1
            fresh.sources = list(dict.fromkeys(fresh.sources + [fresh.source]))
            fresh.original_urls = list(dict.fromkeys(fresh.original_urls + [fresh.url]))
            output.append(fresh)
        fresh.source_count = len(fresh.sources)
    return output, metrics
