import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
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

    @abstractmethod
    async def create_discovery_run(self, query: str, limit_per_source: int) -> str | None:
        raise NotImplementedError

    @abstractmethod
    async def update_discovery_run(self, run_id: str, status: str, stored_count: int, discovered_count: int, errors: dict[str, str]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def store_raw_jobs(self, run_id: str, raw_jobs: list[Any]) -> None:
        raise NotImplementedError


class LocalJsonRepository(Repository):
    def __init__(self, path: Path):
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Initialized LocalJsonRepository with canonical path: {self.path}")
        if not self.path.exists():
            self._write([job.model_dump(mode="json") for job in sample_jobs()])
        else:
            # Self-healing database cleanup on startup: filter out false positives and update ranking
            try:
                from app.pipeline.filters import is_phase_one_candidate
                from app.pipeline.scorer import score_job
                raw_items = self._read()
                jobs_in_db = []
                for item in raw_items:
                    try:
                        jobs_in_db.append(Job.model_validate(item))
                    except Exception as e:
                        logger.warning(f"Skipping invalid database record: {e}")
                
                cleaned = []
                removed_count = 0
                for j in jobs_in_db:
                    if is_phase_one_candidate(j):
                        j = score_job(j)
                        cleaned.append(j)
                    else:
                        removed_count += 1
                if removed_count > 0:
                    logger.info(f"Cleaned up {removed_count} false positives from canonical JSON store.")
                    # Re-sort using match_score DESC, trust_score DESC, date DESC
                    def sort_key(item: Job):
                        date_val = item.date_posted or item.date_discovered
                        if date_val and date_val.tzinfo:
                            date_val = date_val.replace(tzinfo=None)
                        return (
                            item.match_score,
                            item.company.trust_score,
                            date_val or datetime.min
                        )
                    cleaned_sorted = sorted(cleaned, key=sort_key, reverse=True)
                    self._write([j.model_dump(mode="json") for j in cleaned_sorted])
            except Exception as e:
                logger.error(f"Failed to clean database on startup: {e}")

    async def list_jobs(self) -> list[Job]:
        return [Job.model_validate(item) for item in self._read()]

    async def upsert_jobs(self, jobs: list[Job]) -> list[Job]:
        from app.pipeline.dedupe import canonical_company, canonical_title, canonical_domain, titles_are_similar
        from app.models import CompensationStatus
        import logging
        logger = logging.getLogger(__name__)

        # Load existing jobs
        db_jobs = await self.list_jobs()
        
        # We will keep maps of existing jobs for quick lookup and duplicate merging
        primary_map = {}
        secondary_map = {}
        
        for j in db_jobs:
            cc = canonical_company(j.company.name)
            ct = canonical_title(j.title)
            primary_map[(cc, ct)] = j
            
            cd = canonical_domain(j.url)
            if cd:
                if (cc, cd) not in secondary_map:
                    secondary_map[(cc, cd)] = []
                secondary_map[(cc, cd)].append(j)

        excluded_company_ids = {
            j.company.id for j in db_jobs
            if j.company.excluded and j.company.id
        }

        def richest_compensation(c1: str | None, c2: str | None) -> str | None:
            if not c1:
                return c2
            if not c2:
                return c1
            c1_lower = c1.lower()
            c2_lower = c2.lower()
            if c1_lower == "paid stipend":
                return c2
            if c2_lower == "paid stipend":
                return c1
            return c1 if len(c1) >= len(c2) else c2

        for incoming in jobs:
            # Re-run score_job to ensure match_score, priority, and skills are populated
            from app.pipeline.scorer import score_job
            incoming = score_job(incoming)
            
            company_id = company_fingerprint(incoming.company.name, incoming.company.website_url)
            incoming.company.id = company_id
            if company_id in excluded_company_ids:
                incoming.company.excluded = True
                incoming.company.trust_score = 0
                incoming.company.suspicious = True
                incoming.suspicious = True

            cc_in = canonical_company(incoming.company.name)
            ct_in = canonical_title(incoming.title)
            cd_in = canonical_domain(incoming.url)

            # Look for duplicate using primary rule
            matched_job = primary_map.get((cc_in, ct_in))
            
            # If primary fails, try secondary rule
            if not matched_job and cd_in:
                candidates = secondary_map.get((cc_in, cd_in), [])
                for cand in candidates:
                    if titles_are_similar(cand.title, incoming.title):
                        matched_job = cand
                        break

            if matched_job:
                # Merge duplicate
                if not matched_job.first_seen:
                    matched_job.first_seen = matched_job.date_discovered
                matched_job.last_seen = datetime.utcnow()
                matched_job.source_count += 1
                
                # store all source names in sources[]
                if not matched_job.sources:
                    matched_job.sources = [matched_job.source]
                if incoming.source not in matched_job.sources:
                    matched_job.sources.append(incoming.source)
                    
                # keep highest trust score
                if incoming.company.trust_score > matched_job.company.trust_score:
                    matched_job.company.trust_score = incoming.company.trust_score
                    matched_job.company.trust_reasons = incoming.company.trust_reasons
                    
                # keep richest compensation data
                matched_job.compensation = richest_compensation(matched_job.compensation, incoming.compensation)
                if matched_job.compensation and "unpaid" not in matched_job.compensation.lower():
                    matched_job.compensation_status = CompensationStatus.paid
                
                # Keep longest description
                if len(incoming.description) > len(matched_job.description):
                    matched_job.description = incoming.description
                
                # Recalculate match score on merged
                matched_job = score_job(matched_job)
            else:
                # New job
                incoming.id = job_fingerprint(incoming)
                incoming.first_seen = incoming.date_discovered or datetime.utcnow()
                incoming.last_seen = datetime.utcnow()
                incoming.source_count = 1
                incoming.sources = [incoming.source]
                
                # Calculate ranking
                incoming = score_job(incoming)
                
                # Add to maps for subsequent items in batch
                primary_map[(cc_in, ct_in)] = incoming
                if cd_in:
                    if (cc_in, cd_in) not in secondary_map:
                        secondary_map[(cc_in, cd_in)] = []
                    secondary_map[(cc_in, cd_in)].append(incoming)

        # Build list of unique jobs and compute days_since_seen / is_new
        unique_jobs = list(primary_map.values())
        now = datetime.utcnow()
        for j in unique_jobs:
            if not j.first_seen:
                j.first_seen = j.date_discovered
            fs = j.first_seen
            if fs.tzinfo:
                fs = fs.replace(tzinfo=None)
            j.days_since_seen = (now - fs).days
            j.is_new = (now - fs).total_seconds() <= 86400

        # Sort all jobs by match_score DESC, trust_score DESC, date DESC
        def sort_key(item: Job):
            date_val = item.date_posted or item.date_discovered
            if date_val and date_val.tzinfo:
                date_val = date_val.replace(tzinfo=None)
            return (
                item.match_score,
                item.company.trust_score,
                date_val or datetime.min
            )

        output = sorted(unique_jobs, key=sort_key, reverse=True)
        self._write([job.model_dump(mode="json") for job in output])
        return unique_jobs

    async def suspicious_companies(self) -> list[Company]:
        jobs = await self.list_jobs()
        companies: dict[str, Company] = {}
        for job in jobs:
            if job.company.suspicious and not job.company.excluded:
                companies[job.company.id or job.company.name] = job.company
        return sorted(companies.values(), key=lambda company: company.trust_score)

    async def create_discovery_run(self, query: str, limit_per_source: int) -> str | None:
        import uuid
        return str(uuid.uuid4())

    async def update_discovery_run(self, run_id: str, status: str, stored_count: int, discovered_count: int, errors: dict[str, str]) -> None:
        pass

    async def store_raw_jobs(self, run_id: str, raw_jobs: list[Any]) -> None:
        pass

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
        if not jobs:
            return jobs

        # Fetch existing excluded company IDs to preserve exclusion status
        try:
            excluded_response = (
                self.client.table("companies")
                .select("id")
                .eq("excluded", True)
                .execute()
            )
            db_excluded_ids = {row["id"] for row in excluded_response.data}
        except Exception:
            db_excluded_ids = set()

        companies_to_upsert = {}
        jobs_to_upsert = []
        skills_to_upsert = []
        unique_tags = set()

        for job in jobs:
            company_id = company_fingerprint(job.company.name, job.company.website_url)
            job_id = job_fingerprint(job)
            job.company.id = company_id
            job.id = job_id

            if company_id in db_excluded_ids:
                job.company.excluded = True
                job.company.trust_score = 0
                job.company.suspicious = True
                job.suspicious = True

            # Deduplicate companies by ID in the upsert payload
            companies_to_upsert[company_id] = {
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

            jobs_to_upsert.append({
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
                "first_seen": job.first_seen.isoformat() if job.first_seen else job.date_discovered.isoformat(),
                "last_seen": job.last_seen.isoformat() if job.last_seen else datetime.utcnow().isoformat(),
                "sources": [s.value for s in job.sources],
                "source_count": job.source_count,
                "match_score": job.match_score,
                "application_priority": job.application_priority,
                "application_status": job.application_status,
                "match_reasons": job.match_reasons,
                "matching_skills": job.matching_skills,
                "missing_skills": job.missing_skills,
                "days_since_seen": job.days_since_seen,
            })

            for skill in job.required_skills:
                skills_to_upsert.append({
                    "job_id": job_id,
                    "skill": skill,
                    "skill_type": "required",
                })
            for skill in job.preferred_skills:
                skills_to_upsert.append({
                    "job_id": job_id,
                    "skill": skill,
                    "skill_type": "preferred",
                })

            for tag in job.tags:
                unique_tags.add(tag)

        # Batch execute POST requests
        self.client.table("companies").upsert(list(companies_to_upsert.values())).execute()
        self.client.table("jobs").upsert(jobs_to_upsert).execute()

        if skills_to_upsert:
            self.client.table("job_skills").upsert(skills_to_upsert).execute()

        if unique_tags:
            tags_payload = [{"id": t.lower(), "label": t} for t in unique_tags]
            self.client.table("tags").upsert(tags_payload).execute()

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

    async def create_discovery_run(self, query: str, limit_per_source: int) -> str | None:
        try:
            response = self.client.table("discovery_runs").insert({
                "status": "running",
                "query": query,
                "limit_per_source": limit_per_source,
                "errors": {}
            }).execute()
            if response.data:
                return response.data[0]["id"]
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to create discovery run: {e}")
        return None

    async def update_discovery_run(self, run_id: str, status: str, stored_count: int, discovered_count: int, errors: dict[str, str]) -> None:
        if not run_id:
            return
        try:
            self.client.table("discovery_runs").update({
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "status": status,
                "stored_count": stored_count,
                "discovered_count": discovered_count,
                "errors": errors
            }).eq("id", run_id).execute()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to update discovery run: {e}")

    async def store_raw_jobs(self, run_id: str, raw_jobs: list[Any]) -> None:
        if not run_id or not raw_jobs:
            return
        payload = []
        for raw in raw_jobs:
            import hashlib
            key = f"{raw.source.value}|{raw.source_id or raw.url}"
            raw_id = hashlib.md5(key.encode("utf-8")).hexdigest()
            payload.append({
                "id": raw_id,
                "run_id": run_id,
                "source_platform": raw.source.value,
                "source_id": raw.source_id,
                "url": raw.url,
                "company_name": raw.company_name,
                "title": raw.title,
                "raw_data": raw.model_dump(mode="json")
            })
        try:
            self.client.table("raw_jobs").upsert(payload).execute()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to store raw jobs: {e}")

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
            "first_seen": row.get("first_seen"),
            "last_seen": row.get("last_seen"),
            "sources": row.get("sources") or [],
            "source_count": row.get("source_count") or 1,
            "match_score": row.get("match_score") or 0,
            "application_priority": row.get("application_priority") or "Low Priority",
            "application_status": row.get("application_status") or "not_applied",
            "match_reasons": row.get("match_reasons") or [],
            "matching_skills": row.get("matching_skills") or [],
            "missing_skills": row.get("missing_skills") or [],
            "days_since_seen": row.get("days_since_seen") or 0,
        }
        return Job.model_validate(data)


def make_repository(settings: Settings) -> Repository:
    if settings.supabase_enabled:
        return SupabaseRepository(settings)
    return LocalJsonRepository(settings.data_path)

