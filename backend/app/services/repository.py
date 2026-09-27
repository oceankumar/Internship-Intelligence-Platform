import asyncio
import json
import hashlib
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import fcntl

from app.config import Settings
from app.models import CandidateProfile, Company, Job
from app.pipeline.dedupe import merge_jobs


def load_job(data: dict) -> Job:
    job = Job.model_validate(data)
    if str(job.id or "").startswith("sample-"):
        job.provenance["sample"] = True
        job.hidden = True
    if not data.get("provenance") and not (data.get("intelligence") or {}).get("provenance"):
        job.provenance["legacy_record"] = True
        if job.source in {"simplify_jobs", "github_jobs", "startup_career_pages"} and job.compensation == "Paid stipend":
            job.provenance["legacy_compensation"] = "Unverified generic value from the old provider; not evidence of pay"
            job.compensation = None
            from app.pipeline.normalizer import normalize_compensation
            job.compensation_status = normalize_compensation(None, job.description)
        if job.source == "public_datasets":
            job.provenance["listing_kind"] = "program_catalog"
            job.date_posted = None
            from app.models import RemoteStatus
            job.remote_status = RemoteStatus.unknown
    return job


class Repository:
    async def list_jobs(self) -> list[Job]:
        raise NotImplementedError

    async def upsert_jobs(self, jobs: list[Job]) -> list[Job]:
        raise NotImplementedError

    async def patch_job(self, job_id: str, changes: dict) -> Job | None:
        raise NotImplementedError

    async def get_state(self, key: str, default: Any = None) -> Any:
        raise NotImplementedError

    async def put_state(self, key: str, value: Any) -> None:
        raise NotImplementedError

    async def profile(self) -> CandidateProfile:
        return CandidateProfile.model_validate(await self.get_state("profile", {}))

    async def suspicious_companies(self) -> list[Company]:
        return list({j.company.id or j.company.name: j.company for j in await self.list_jobs() if j.suspicious}.values())

    async def create_discovery_run(self, query: str, limit_per_source: int) -> str:
        run_id = str(uuid4())
        await self.put_state("run:" + run_id, {"id": run_id, "query": query, "limit_per_source": limit_per_source, "status": "running", "started_at": datetime.now(timezone.utc).isoformat()})
        return run_id

    async def update_discovery_run(self, run_id: str, status: str, stored_count: int, discovered_count: int, errors: dict, **details) -> None:
        run = await self.get_state("run:" + run_id, {})
        run.update(status=status, stored_count=stored_count, discovered_count=discovered_count, errors=errors, completed_at=datetime.now(timezone.utc).isoformat(), **details)
        await self.put_state("run:" + run_id, run)

    async def store_raw_jobs(self, run_id: str, raw_jobs: list[Any]) -> None:
        await self.put_state("raw:" + run_id, [j.model_dump(mode="json") for j in raw_jobs])

    async def list_runs(self) -> list[dict]:
        raise NotImplementedError


class LocalJsonRepository(Repository):
    """Single-host storage. Reads never reclassify or delete historical records."""
    def __init__(self, path: Path):
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path = self.path.with_suffix(".state.json")
        with self._lock():
            if not self.path.exists():
                self._write([])

    @contextmanager
    def _lock(self):
        with self.path.with_suffix(".lock").open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def _read(self):
        return json.loads(self.path.read_text())

    def _atomic(self, path: Path, data: Any):
        fd, temporary = tempfile.mkstemp(dir=path.parent)
        try:
            with os.fdopen(fd, "w") as handle:
                json.dump(data, handle, indent=2, default=str)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _write(self, rows):
        self._atomic(self.path, rows)

    async def list_jobs(self) -> list[Job]:
        return await asyncio.to_thread(lambda: [load_job(j) for j in self._read()])

    async def upsert_jobs(self, jobs: list[Job]) -> list[Job]:
        def write():
            with self._lock():
                merged, _ = merge_jobs([load_job(j) for j in self._read()], jobs)
                self._write([j.model_dump(mode="json") for j in merged])
                return merged
        return await asyncio.to_thread(write)

    async def patch_job(self, job_id: str, changes: dict) -> Job | None:
        def write():
            with self._lock():
                jobs = [Job.model_validate(j) for j in self._read()]
                job = next((j for j in jobs if j.id == job_id), None)
                if not job:
                    return None
                updated = Job.model_validate({**job.model_dump(), **changes})
                jobs[jobs.index(job)] = updated
                self._write([j.model_dump(mode="json") for j in jobs])
                return updated
        return await asyncio.to_thread(write)

    def _state(self) -> dict:
        return json.loads(self.state_path.read_text()) if self.state_path.exists() else {}

    async def get_state(self, key: str, default: Any = None) -> Any:
        return await asyncio.to_thread(lambda: self._state().get(key, default))

    async def put_state(self, key: str, value: Any) -> None:
        def write():
            with self._lock():
                state = self._state()
                state[key] = value
                # Keep diagnostics bounded; raw payloads have a shorter retention.
                for prefix, keep in [("run:", 100), ("raw:", 10), ("ai:", 1000)]:
                    keys = [k for k in state if k.startswith(prefix)]
                    for old in keys[:-keep]:
                        del state[old]
                self._atomic(self.state_path, state)
        await asyncio.to_thread(write)

    async def list_runs(self) -> list[dict]:
        return sorted([v for k, v in self._state().items() if k.startswith("run:")], key=lambda r: r["started_at"], reverse=True)


class SupabaseRepository(Repository):
    def __init__(self, settings: Settings):
        from supabase import create_client
        self.client = create_client(settings.supabase_url, settings.supabase_service_role_key)

    async def list_jobs(self) -> list[Job]:
        def read():
            rows, offset = [], 0
            while True:
                batch = self.client.table("jobs").select("*, companies(*)").order("id").range(offset, offset + 499).execute().data
                rows.extend(self._job_from_row(r) for r in batch)
                if len(batch) < 500:
                    return rows
                offset += 500
        return await asyncio.to_thread(read)

    def _job_from_row(self, row: dict) -> Job:
        data = {**row, **(row.get("intelligence") or {}), "company": row["companies"], "source": row["source_platform"]}
        data["notes"] = data.get("notes") or ""
        return load_job(data)

    async def upsert_jobs(self, jobs: list[Job]) -> list[Job]:
        if not jobs:
            return await self.list_jobs()
        merged, _ = merge_jobs(await self.list_jobs(), jobs)
        incoming_urls = {u for j in jobs for u in [j.url, *j.original_urls]}
        affected = [j for j in merged if incoming_urls.intersection([j.url, *j.original_urls])]
        # Transactional RPC preserves user state even if tracking changes during ingestion.
        await asyncio.to_thread(lambda: self.client.rpc("upsert_intelligence_jobs", {"payload": [j.model_dump(mode="json") for j in affected]}).execute())
        return await self.list_jobs()

    async def patch_job(self, job_id: str, changes: dict) -> Job | None:
        result = await asyncio.to_thread(lambda: self.client.rpc("patch_intelligence_job", {"job_id": job_id, "changes": changes}).execute())
        if not result.data:
            return None
        return self._job_from_row(result.data)

    async def get_state(self, key: str, default: Any = None) -> Any:
        if key.startswith("run:"):
            result = await asyncio.to_thread(lambda: self.client.table("discovery_runs").select("*").eq("id", key[4:]).execute())
            return ({**result.data[0], **result.data[0].get("details", {})} if result.data else default)
        response = await asyncio.to_thread(lambda: self.client.table("intelligence_state").select("value").eq("key", key).execute())
        return response.data[0]["value"] if response.data else default

    async def put_state(self, key: str, value: Any) -> None:
        if key.startswith("run:"):
            columns = {k: value[k] for k in ("id", "started_at", "completed_at", "status", "query", "limit_per_source", "stored_count", "discovered_count", "errors") if k in value}
            columns["details"] = {k: v for k, v in value.items() if k not in columns and k != "details"}
            await asyncio.to_thread(lambda: self.client.table("discovery_runs").upsert(columns).execute())
            return
        await asyncio.to_thread(lambda: self.client.table("intelligence_state").upsert({"key": key, "value": value, "updated_at": datetime.now(timezone.utc).isoformat()}).execute())

    async def store_raw_jobs(self, run_id: str, raw_jobs: list[Any]) -> None:
        rows = [{"id": hashlib.sha256(f"{run_id}:{i}:{j.url}".encode()).hexdigest()[:32], "run_id": run_id, "source_platform": j.source.value, "source_id": j.source_id, "url": j.url, "company_name": j.company_name, "title": j.title, "raw_data": j.model_dump(mode="json")} for i, j in enumerate(raw_jobs)]
        for start in range(0, len(rows), 250):
            await asyncio.to_thread(lambda: self.client.table("raw_jobs").insert(rows[start:start+250]).execute())

    async def list_runs(self) -> list[dict]:
        response = await asyncio.to_thread(lambda: self.client.table("discovery_runs").select("*").order("started_at", desc=True).limit(100).execute())
        return [{**r, **r.get("details", {})} for r in response.data]


def make_repository(settings: Settings) -> Repository:
    return SupabaseRepository(settings) if settings.supabase_enabled else LocalJsonRepository(settings.data_path)
