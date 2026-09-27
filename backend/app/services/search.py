import re
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from app.models import Job
from app.pipeline.lifecycle import utc
from app.pipeline.normalizer import extract_skills


class Filters(BaseModel):
    q: str = Field(default="", max_length=500)
    role: str = ""
    skill: str = ""
    remote: str = ""
    country: str = ""
    company: str = ""
    paid: bool = False
    source: str = ""
    status: str = ""
    favorite: bool = False
    include_hidden: bool = False
    include_inactive: bool = False
    min_match: int = Field(default=0, ge=0, le=100)
    min_trust: int = Field(default=0, ge=0, le=100)
    min_opportunity: int = Field(default=0, ge=0, le=100)
    posted_days: int | None = Field(default=None, ge=1, le=3650)
    closing_days: int | None = Field(default=None, ge=1, le=365)
    max_experience: int | None = Field(default=None, ge=0, le=600)
    min_stipend: float | None = Field(default=None, ge=0)
    currency: str = ""
    period: str = ""
    applications: bool = False
    recommended: bool = False


def parse_query(q: str) -> dict[str, str | bool]:
    lower = q.lower()
    parsed: dict[str, str | bool] = {}
    if re.search(r"\bpaid\b", lower):
        parsed["paid"] = True
    for mode in ("remote", "hybrid", "onsite"):
        if re.search(rf"\b{mode}\b", lower):
            parsed["remote"] = mode
    for role in ("frontend", "backend", "full-stack", "data science", "software engineering"):
        if role in lower:
            parsed["role"] = role
    skills = extract_skills(lower)
    if skills:
        parsed["skill"] = ",".join(skills)
    return parsed


def filter_jobs(jobs: list[Job], f: Filters) -> list[Job]:
    now = datetime.now(timezone.utc)
    semantic = parse_query(f.q) if len(f.q.split()) > 4 else {}
    effective = f.model_copy(update={k: v for k, v in semantic.items() if not getattr(f, k)})
    output = []
    for j in jobs:
        if j.internship is False and not f.include_hidden:
            continue
        if (j.hidden or j.company.excluded) and not f.include_hidden:
            continue
        if not j.active and not f.include_inactive:
            continue
        if f.q and not semantic and f.q.casefold() not in " ".join([j.title, j.company.name, j.description, j.location or "", *j.required_skills]).casefold():
            continue
        if effective.role and j.role_family != effective.role:
            continue
        if effective.skill and not {s.strip().lower() for s in effective.skill.split(",") if s.strip()}.issubset({s.lower() for s in j.required_skills + j.preferred_skills}):
            continue
        if effective.remote and j.remote_status != effective.remote:
            continue
        if f.country and f.country.lower() not in (j.country or j.location or "").lower():
            continue
        if f.company and f.company.lower() not in j.company.name.lower():
            continue
        if effective.paid and j.compensation_status != "paid":
            continue
        if f.source and f.source not in j.sources:
            continue
        if f.status and j.application_status != f.status:
            continue
        if f.favorite and not j.favorite:
            continue
        if f.applications and j.application_status == "not_applied":
            continue
        if f.recommended and j.application_priority not in {"Apply Now", "Strong Match"}:
            continue
        if j.match_score < f.min_match or j.company.trust_score < f.min_trust or j.opportunity_score < f.min_opportunity:
            continue
        if f.posted_days and (not j.date_posted or utc(j.date_posted) < now - timedelta(days=f.posted_days)):
            continue
        if f.closing_days and (not j.deadline or not now <= utc(j.deadline) <= now + timedelta(days=f.closing_days)):
            continue
        if f.max_experience is not None and j.minimum_experience_months is not None and j.minimum_experience_months > f.max_experience:
            continue
        if f.min_stipend is not None and (j.stipend_min is None or j.stipend_min < f.min_stipend or not f.currency or not f.period):
            continue
        if f.currency and j.compensation_currency != f.currency:
            continue
        if f.period and j.compensation_period != f.period:
            continue
        output.append(j)
    return output


def sort_jobs(jobs: list[Job], sort: str) -> list[Job]:
    def key(j: Job):
        if sort == "newest":
            return utc(j.date_posted or j.date_discovered).timestamp()
        if sort == "match":
            return j.match_score
        if sort == "trust":
            return j.company.trust_score
        if sort == "deadline":
            return -(utc(j.deadline).timestamp()) if j.deadline else float("-inf")
        if sort == "stipend":
            return j.stipend_min if j.stipend_min is not None else -1
        return j.opportunity_score
    return sorted(jobs, key=lambda j: (key(j), j.id or j.url), reverse=True)
