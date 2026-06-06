import hashlib
import re

from app.models import Job


def job_fingerprint(job: Job) -> str:
    # We still need a unique stable ID for storage.
    # The user says "Do NOT use job_id as the primary deduplication key."
    # That means when merging, we check company + title normalized, not just job_id.
    # But we can still generate a deterministic id using the primary merge key!
    c_comp = canonical_company(job.company.name)
    c_title = canonical_title(job.title)
    key = f"{c_comp}|{c_title}".lower()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def company_fingerprint(name: str, website_url: str | None = None) -> str:
    website = canonical_domain(website_url) if website_url else ""
    key = website or re.sub(r"[^a-z0-9]+", "", name.lower())
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def canonical_url(url: str) -> str:
    if not url:
        return ""
    return url.split("?")[0].rstrip("/").strip().lower()


def canonical_domain(url: str | None) -> str:
    if not url:
        return ""
    cleaned = url.replace("https://", "").replace("http://", "").split("/")[0]
    return cleaned.removeprefix("www.").lower()


def canonical_company(name: str) -> str:
    n = name.lower().strip()
    n = re.sub(r"\b(inc|corp|co|ltd|llc|gmbh|software|technologies|labs|systems)\b", "", n)
    n = re.sub(r"[^a-z0-9]", "", n)
    return n.strip()


def canonical_title(title: str) -> str:
    t = title.lower().strip()
    t = t.encode('ascii', 'ignore').decode('ascii') # remove emojis
    t = re.sub(r"[^a-z0-9\s\-]", " ", t)
    # standardize title representations
    t = re.sub(r"\b(internship|intern)\b", "intern", t)
    t = re.sub(r"\b(co-op|coop)\b", "coop", t)
    t = re.sub(r"\b(swe)\b", "software engineer", t)
    t = re.sub(r"\b(dev)\b", "developer", t)
    t = re.sub(r"\b(front end|front-end)\b", "frontend", t)
    t = re.sub(r"\b(back end|back-end)\b", "backend", t)
    t = re.sub(r"\b(full stack|full-stack)\b", "fullstack", t)
    return " ".join(t.split())


def titles_are_similar(title1: str, title2: str) -> bool:
    t1 = canonical_title(title1)
    t2 = canonical_title(title2)
    if t1 == t2:
        return True
    words1 = set(t1.split())
    words2 = set(t2.split())
    core_keywords = {"software", "engineer", "developer", "frontend", "backend", "fullstack", "ai", "ml", "data", "react", "next", "design", "firmware", "embedded"}
    t1_core = words1.intersection(core_keywords)
    t2_core = words2.intersection(core_keywords)
    if t1_core and t2_core:
        return len(t1_core.intersection(t2_core)) > 0
    return False


