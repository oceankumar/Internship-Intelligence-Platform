from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


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
    date_discovered: datetime = Field(default_factory=datetime.utcnow)
    relevance_score: int = 0
    score_reasons: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    suspicious: bool = False


class DiscoveryRequest(BaseModel):
    sources: list[SourceName] | None = None
    query: str = "frontend react next.js internship paid remote"
    limit_per_source: int = Field(default=25, ge=1, le=100)
    persist: bool = True


class DiscoveryResponse(BaseModel):
    discovered: int
    stored: int
    jobs: list[Job]
    errors: dict[str, str] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    storage: str

