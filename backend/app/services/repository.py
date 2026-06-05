import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.config import Settings
from app.models import Company, Job
from app.pipeline.dedupe import company_fingerprint, job_fingerprint
from app.sample_data import sample_jobs


class Repository(ABC):
    @abstractmethod
    async def list_jobs(self) -> list[Job]:
        raise NotImplementedError

    @abstractmethod
    async def upsert_jobs(self, jobs: list[Job]) -> list[Job]:
        raise NotImplementedError

    @abstractmethod
    async def suspicious_companies(self) -> list[Company]:
        raise NotImplementedError


class LocalJsonRepository(Repository):
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([job.model_dump(mode="json") for job in sample_jobs()])

    async def list_jobs(self) -> list[Job]:
        return [Job.model_validate(item) for item in self._read()]

    async def upsert_jobs(self, jobs: list[Job]) -> list[Job]:
        existing = {job_fingerprint(job): job for job in await self.list_jobs()}
        for job in jobs:
            job.id = job_fingerprint(job)
            job.company.id = company_fingerprint(job.company.name, job.company.website_url)
            existing[job.id] = job
        output = sorted(existing.values(), key=lambda item: item.relevance_score, reverse=True)
        self._write([job.model_dump(mode="json") for job in output])
        return jobs

    async def suspicious_companies(self) -> list[Company]:
        jobs = await self.list_jobs()
        companies: dict[str, Company] = {}
        for job in jobs:
            if job.company.suspicious and not job.company.excluded:
                companies[job.company.id or job.company.name] = job.company
        return sorted(companies.values(), key=lambda company: company.trust_score)

    def _read(self) -> list[dict[str, Any]]:
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, rows: list[dict[str, Any]]) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(rows, handle, indent=2)


class SupabaseRepository(Repository):
    def __init__(self, settings: Settings):
        try:
            from supabase import create_client
        except ImportError as exc:
            raise RuntimeError("Install backend requirements to use Supabase storage") from exc
        self.client = create_client(settings.supabase_url, settings.supabase_service_role_key)

    async def list_jobs(self) -> list[Job]:
        response = (
            self.client.table("jobs")
            .select("*, companies(*)")
            .order("relevance_score", desc=True)
            .execute()
        )
        return [self._job_from_row(row) for row in response.data]

    async def upsert_jobs(self, jobs: list[Job]) -> list[Job]:
        for job in jobs:
            company_id = company_fingerprint(job.company.name, job.company.website_url)
            job_id = job_fingerprint(job)
            job.company.id = company_id
            job.id = job_id
            self.client.table("companies").upsert(
                {
                    "id": company_id,
                    "name": job.company.name,
                    "website_url": job.company.website_url,
                    "linkedin_url": job.company.linkedin_url,
                    "description": job.company.description,
                    "trust_score": job.company.trust_score,
                    "suspicious": job.company.suspicious,
                    "trust_reasons": job.company.trust_reasons,
                    "excluded": job.company.excluded,
                }
            ).execute()
            self.client.table("jobs").upsert(
                {
                    "id": job_id,
                    "company_id": company_id,
                    "title": job.title,
                    "url": job.url,
                    "description": job.description,
                    "required_skills": job.required_skills,
                    "preferred_skills": job.preferred_skills,
                    "location": job.location,
                    "remote_status": job.remote_status.value,
                    "internship_type": job.internship_type,
                    "compensation": job.compensation,
                    "compensation_status": job.compensation_status.value,
                    "source_platform": job.source.value,
                    "source_id": job.source_id,
                    "date_posted": job.date_posted.isoformat() if job.date_posted else None,
                    "date_discovered": job.date_discovered.isoformat(),
                    "relevance_score": job.relevance_score,
                    "score_reasons": job.score_reasons,
                    "tags": job.tags,
                    "suspicious": job.suspicious,
                }
            ).execute()
        return jobs

    async def suspicious_companies(self) -> list[Company]:
        response = (
            self.client.table("companies")
            .select("*")
            .eq("suspicious", True)
            .eq("excluded", False)
            .order("trust_score")
            .execute()
        )
        return [Company.model_validate(row) for row in response.data]

    def _job_from_row(self, row: dict[str, Any]) -> Job:
        company_row = row.pop("companies", None) or {}
        data = {
            "id": row.get("id"),
            "company": Company.model_validate(company_row),
            "title": row.get("title"),
            "url": row.get("url"),
            "description": row.get("description") or "",
            "required_skills": row.get("required_skills") or [],
            "preferred_skills": row.get("preferred_skills") or [],
            "location": row.get("location"),
            "remote_status": row.get("remote_status") or "unknown",
            "internship_type": row.get("internship_type") or "internship",
            "compensation": row.get("compensation"),
            "compensation_status": row.get("compensation_status") or "unknown",
            "source": row.get("source_platform"),
            "source_id": row.get("source_id"),
            "date_posted": row.get("date_posted"),
            "date_discovered": row.get("date_discovered"),
            "relevance_score": row.get("relevance_score") or 0,
            "score_reasons": row.get("score_reasons") or [],
            "tags": row.get("tags") or [],
            "suspicious": row.get("suspicious") or False,
        }
        return Job.model_validate(data)


def make_repository(settings: Settings) -> Repository:
    if settings.supabase_enabled:
        return SupabaseRepository(settings)
    return LocalJsonRepository(settings.data_path)

