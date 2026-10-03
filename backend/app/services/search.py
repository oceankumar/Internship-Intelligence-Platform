import re
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from app.models import Job
from app.pipeline.lifecycle import utc
from app.pipeline.normalizer import extract_skills
from app.pipeline.normalizer import SKILL_ALIASES
from app.pipeline.geography import COUNTRIES, canonical_country


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
    include_risky: bool = False
    include_programs: bool = False
    discovered_days: int | None = Field(default=None, ge=1, le=3650)


def parse_query(q: str) -> dict[str, str | bool]:
    return interpret_query(q)["filters"]


def interpret_query(q: str) -> dict:
    lower = q.lower()
    parsed: dict[str, str | bool] = {}
    residual = lower
    def consume(pattern):
        nonlocal residual
        residual = re.sub(pattern, " ", residual, flags=re.I)
    if re.search(r"\bpaid\b", lower):
        parsed["paid"] = True
        consume(r"\bpaid\b")
    modes = [mode for mode in ("remote", "hybrid", "onsite") if re.search(rf"\b{mode}\b", lower)]
    if len(modes) == 1:
        parsed["remote"] = modes[0]
        consume(rf"\b{modes[0]}\b")
    roles = [(role,pattern) for role,pattern in [("frontend",r"front[ -]?end"),("backend",r"back[ -]?end"),("full-stack",r"full[ -]?stack"),("data science",r"data science"),("software engineering",r"software(?: engineering| engineer)?"),("AI/ML",r"ai|machine learning")] if re.search(rf"\b(?:{pattern})\b",lower)]
    if len(roles) == 1:
        parsed["role"] = roles[0][0]
        consume(rf"\b(?:{roles[0][1]})\b")
    countries = [(country, pattern) for country, pattern in COUNTRIES.items() if re.search(rf"\b(?:{pattern})\b", q, re.I)]
    if len(countries) == 1:
        parsed["country"] = countries[0][0]
        consume(rf"\b(?:{countries[0][1]})\b")
    skills = extract_skills(lower)
    if skills:
        parsed["skill"] = ",".join(skills)
        for skill in skills:
            for alias in SKILL_ALIASES[skill]:
                consume(rf"\b{re.escape(alias)}\b")
    consume(r"\b(?:show|find|me|please|looking|for|a|an|the|and|with|in|at|based|opportunities|roles?|jobs?|internships?|interns?|students?|engineering|developer)\b")
    unparsed = " ".join(residual.strip(" ,.").split()) if parsed else q.strip()
    warnings = ["Remaining text is matched literally; it has not been interpreted as eligibility."] if parsed and unparsed else []
    if re.search(r'\bstudents?\b',lower):
        warnings.append("Student eligibility must be checked in the listing; the query does not verify enrollment requirements.")
    if re.search(r'\b(?:not|no)\s+(?:paid|remote|hybrid|onsite|frontend|backend)',lower):
        return {"filters": {}, "unparsed": q.strip(), "warnings": ["Negated constraints are unsupported; the complete query is retained as literal text."]}
    return {"filters": parsed, "unparsed": unparsed, "warnings": warnings}


def filter_jobs(jobs: list[Job], f: Filters) -> list[Job]:
    now = datetime.now(timezone.utc)
    interpretation = interpret_query(f.q)
    semantic = interpretation["filters"]
    effective = f.model_copy(update={k: v for k, v in semantic.items() if not getattr(f, k)})
    output = []
    for j in jobs:
        if j.risk_state in {"quarantined", "blocked"} and not f.include_risky:
            continue
        if j.opportunity_type != "internship" and not f.include_programs:
            continue
        if j.internship is False and not f.include_hidden:
            continue
        if (j.hidden or j.company.excluded) and not f.include_hidden:
            continue
        if not j.active and not f.include_inactive:
            continue
        search_text = " ".join([j.title, j.company.name, j.description, j.location or "", *j.required_skills, *j.mentioned_skills]).casefold()
        if interpretation["unparsed"] and interpretation["unparsed"].casefold() not in search_text:
            continue
        if any(getattr(f, k) and getattr(f, k) != v for k, v in semantic.items() if k in {"role", "remote", "country"}):
            continue
        if effective.role and j.role_family != effective.role:
            continue
        if effective.skill and not {s.strip().lower() for s in effective.skill.split(",") if s.strip()}.issubset({s.lower() for s in j.required_skills + j.preferred_skills + j.mentioned_skills}):
            continue
        if effective.remote and j.remote_status != effective.remote:
            continue
        if effective.country and canonical_country(effective.country) not in [j.country, *j.remote_countries] and not j.worldwide_remote:
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
        if j.match_score < f.min_match or j.trust_score < f.min_trust or j.opportunity_score < f.min_opportunity:
            continue
        if f.posted_days and (not j.date_posted or utc(j.date_posted) < now - timedelta(days=f.posted_days)):
            continue
        if f.discovered_days and utc(j.first_seen or j.date_discovered) < now - timedelta(days=f.discovered_days):
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
            return j.trust_score
        if sort == "deadline":
            return -(utc(j.deadline).timestamp()) if j.deadline else float("-inf")
        if sort == "stipend":
            return j.stipend_min if j.stipend_min is not None else -1
        return j.opportunity_score
    return sorted(jobs, key=lambda j: (key(j), j.id or j.url), reverse=True)
