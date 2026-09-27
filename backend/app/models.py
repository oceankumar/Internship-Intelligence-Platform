from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class RemoteStatus(str, Enum):
    remote = "remote"
    hybrid = "hybrid"
    onsite = "onsite"
    unknown = "unknown"


class CompensationStatus(str, Enum):
    paid = "paid"
    unpaid = "unpaid"
    unknown = "unknown"


class SourceName(str, Enum):
    remoteok = "remoteok"
    yc_jobs = "yc_jobs"
    work_at_a_startup = "work_at_a_startup"
    wellfound = "wellfound"
    simplify_jobs = "simplify_jobs"
    github_jobs = "github_jobs"
    public_datasets = "public_datasets"
    startup_career_pages = "startup_career_pages"


class RawInternship(BaseModel):
    source: SourceName
    source_id: str | None = None
    title: str
    company_name: str
    url: str
    description: str = ""
    company_description: str | None = None
    company_website: str | None = None
    company_linkedin_url: str | None = None
    location: str | None = None
    remote_status: RemoteStatus = RemoteStatus.unknown
    compensation: str | None = None
    date_posted: datetime | None = None
    deadline: datetime | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class Company(BaseModel):
    id: str | None = None
    name: str
    website_url: str | None = None
    linkedin_url: str | None = None
    description: str | None = None
    trust_score: int = 0
    suspicious: bool = False
    trust_reasons: list[str] = Field(default_factory=list)
    excluded: bool = False


class Job(BaseModel):
    id: str | None = None
    company: Company
    title: str
    url: str
    description: str = ""
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    location: str | None = None
    remote_status: RemoteStatus = RemoteStatus.unknown
    internship_type: str = "internship"
    compensation: str | None = None
    compensation_status: CompensationStatus = CompensationStatus.unknown
    source: SourceName
    source_id: str | None = None
    date_posted: datetime | None = None
    date_discovered: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    relevance_score: int = 0
    score_reasons: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    suspicious: bool = False
    
    # Phase 1.7 & Phase 1.8 fields
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    sources: list[SourceName] = Field(default_factory=list)
    source_count: int = 1
    is_new: bool = True
    days_since_seen: int = 0
    match_score: int = 0
    application_priority: str = "Low Priority"
    application_status: str = "not_applied"
    match_reasons: list[str] = Field(default_factory=list)
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    normalized_title: str = ""
    normalized_company: str = ""
    company_domain: str | None = None
    role_family: str = "other"
    internship: bool | None = None
    country: str | None = None
    stipend_min: float | None = None
    stipend_max: float | None = None
    compensation_currency: str | None = None
    compensation_period: str | None = None
    minimum_experience_months: int | None = None
    graduation_years: list[int] = Field(default_factory=list)
    eligibility_text: str = ""
    summary: str = ""
    deadline: datetime | None = None
    original_urls: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    eligibility_score: int = 50
    eligibility_status: str = "Unclear"
    eligibility_reasons: list[str] = Field(default_factory=list)
    freshness_score: int = 0
    opportunity_score: int = 0
    urgency_score: int = 0
    score_breakdown: dict[str, int] = Field(default_factory=dict)
    match_breakdown: dict[str, int] = Field(default_factory=dict)
    trust_level: str = "unknown"
    active: bool = True
    stale: bool = False
    expired: bool = False
    closed: bool = False
    last_verified_at: datetime | None = None
    favorite: bool = False
    hidden: bool = False
    notes: str = ""
    applied_at: datetime | None = None
    interview_at: datetime | None = None
    reminder_at: datetime | None = None
    contact: str = ""
    corrections: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def init_migration_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Migrate source list
            if not data.get("sources"):
                s = data.get("source")
                if s:
                    data["sources"] = [s]
            # Migrate first_seen/last_seen
            disc = data.get("date_discovered") or datetime.now(timezone.utc).isoformat()
            if not data.get("first_seen"):
                data["first_seen"] = data.get("first_seen") or disc
            if not data.get("last_seen"):
                data["last_seen"] = data.get("last_seen") or disc
        return data



class DiscoveryRequest(BaseModel):
    sources: list[SourceName] | None = None
    query: str = Field(default="internship", max_length=500)
    limit_per_source: int = Field(default=25, ge=1, le=100)
    persist: bool = True


class SourceReport(BaseModel):
    source: str
    raw_jobs: int
    internships: int
    paid_internships: int
    remote_internships: int
    rejected: int = 0
    duplicates: int = 0
    duration_ms: int = 0
    status: str = "healthy"
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)
    rejection_reasons: dict[str, int] = Field(default_factory=dict)


class DiscoveryResponse(BaseModel):
    discovered: int
    stored: int
    jobs: list[Job]
    errors: dict[str, str] = Field(default_factory=dict)
    source_report: list[SourceReport] = Field(default_factory=list)
    run_id: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


ApplicationStatus = Literal["not_applied", "planning", "applied", "assessment", "interview", "offer", "rejected", "withdrawn"]


class CandidateProfile(BaseModel):
    name: str = Field(default="", max_length=120)
    skills: list[str] = Field(default_factory=list, max_length=100)
    preferred_roles: list[str] = Field(default_factory=lambda: ["frontend", "full-stack", "software engineering"], max_length=20)
    experience_months: int = Field(default=0, ge=0, le=600)
    education: str = Field(default="", max_length=300)
    graduation_year: int | None = Field(default=None, ge=2000, le=2100)
    country: str = Field(default="", max_length=100)
    preferred_locations: list[str] = Field(default_factory=list, max_length=30)
    remote_preference: bool = True
    paid_only: bool = True


class ApplicationUpdate(BaseModel):
    application_status: ApplicationStatus | None = None
    favorite: bool | None = None
    hidden: bool | None = None
    notes: str | None = Field(default=None, max_length=5000)
    applied_at: datetime | None = None
    interview_at: datetime | None = None
    reminder_at: datetime | None = None
    contact: str | None = Field(default=None, max_length=300)


class JobCorrection(BaseModel):
    remote_status: RemoteStatus | None = None
    compensation_status: CompensationStatus | None = None
    required_skills: list[str] | None = Field(default=None, max_length=100)


class SavedSearch(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    filters: dict[str, str] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    storage: str
