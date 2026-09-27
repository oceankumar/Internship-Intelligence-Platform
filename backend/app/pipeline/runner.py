import asyncio
import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone
from uuid import uuid4

import httpx

from app.config import Settings
from app.models import DiscoveryRequest, DiscoveryResponse, Job, SourceReport
from app.pipeline.dedupe import merge_jobs
from app.pipeline.filters import rejection_reason
from app.pipeline.normalizer import normalize_job
from app.pipeline.scorer import score_job
from app.providers.registry import get_providers
from app.services.ai import classify
from app.services.repository import Repository

logger = logging.getLogger(__name__)


async def run_discovery(settings: Settings, repository: Repository, request: DiscoveryRequest) -> DiscoveryResponse:
    started = time.monotonic()
    run_id = await repository.create_discovery_run(request.query, request.limit_per_source) if request.persist else str(uuid4())
    profile = await repository.profile()
    providers = get_providers(settings, request.sources)
    semaphore = asyncio.Semaphore(settings.provider_concurrency)
    errors, all_raw, jobs, reports = {}, [], [], []
    ai_counts = Counter()
    rejections = []

    async def collect(provider):
        begin = time.monotonic()
        source = provider.source.value
        report = SourceReport(source=source, raw_jobs=0, internships=0, paid_internships=0, remote_internships=0)
        if source in {"wellfound", "work_at_a_startup"}:
            report.status = "disabled"
            report.error = "Public automated access unavailable; source disabled"
            return report, []
        try:
            async with semaphore:
                raw = await asyncio.wait_for(provider.discover(request.query, request.limit_per_source), timeout=max(30, settings.request_timeout_seconds * 6))
            report.raw_jobs = len(raw)
            report.warnings = provider.warnings
            if not raw or provider.warnings:
                report.status = "degraded"
                if not raw:
                    report.warnings.append("No records returned; empty feed or parser change needs review")
            return report, raw
        except (httpx.TimeoutException, asyncio.TimeoutError):
            report.status, report.error = "failing", "PROVIDER_TIMEOUT"
        except httpx.HTTPStatusError as exc:
            report.status, report.error = "failing", f"HTTP_{exc.response.status_code}"
        except Exception:
            report.status, report.error = "failing", "PROVIDER_PARSE_OR_FETCH_ERROR"
        finally:
            report.duration_ms = round((time.monotonic() - begin) * 1000)
        return report, []

    for report, records in await asyncio.gather(*(collect(p) for p in providers)):
        reports.append(report)
        if report.error:
            errors[report.source] = report.error
        all_raw.extend(records)
        for raw in records:
            try:
                job = normalize_job(raw)
                score_job(job, profile)
                reason = rejection_reason(job)
                if reason:
                    report.rejected += 1
                    report.rejection_reasons[reason] = report.rejection_reasons.get(reason, 0) + 1
                    rejections.append({"source": report.source, "source_id": raw.source_id, "reason": reason})
                    continue
                if request.persist:
                    ai_counts[await classify(job, settings, repository)] += 1
                job.last_seen = datetime.now(timezone.utc)
                score_job(job, profile)
                jobs.append(job)
                report.internships += 1
                report.paid_internships += int(job.compensation_status == "paid")
                report.remote_internships += int(job.remote_status == "remote")
            except Exception:
                report.rejected += 1
                report.rejection_reasons["NORMALIZATION_ERROR"] = report.rejection_reasons.get("NORMALIZATION_ERROR", 0) + 1
                report.status = "degraded"

    existing = await repository.list_jobs()
    merged, counts = merge_jobs(existing, jobs)
    incoming_urls = {u for j in jobs for u in [j.url, *j.original_urls]}
    affected_ids = {j.id for j in merged if incoming_urls.intersection([j.url, *j.original_urls])}
    seen = list(existing)
    from app.pipeline.dedupe import same_job
    for job in jobs:
        if any(same_job(job, old) for old in seen):
            next(r for r in reports if r.source == job.source).duplicates += 1
        seen.append(job)
    metrics = {
        "fetched": len(all_raw), "internships": len(jobs), "rejected": sum(r.rejected for r in reports),
        **counts, "paid": sum(j.compensation_status == "paid" for j in jobs),
        "remote": sum(j.remote_status == "remote" for j in jobs),
        "strong_matches": sum(j.application_priority in {"Apply Now", "Strong Match"} for j in jobs),
        "provider_failures": sum(r.status == "failing" for r in reports),
        "priority_distribution": dict(Counter(j.application_priority for j in jobs)),
        "score_distribution": dict(Counter(f"{j.match_score // 20 * 20}-{min(100, j.match_score // 20 * 20 + 19)}" for j in jobs)),
        "ai": dict(ai_counts),
    }
    status = "failed" if reports and all(r.status in {"failing", "disabled"} for r in reports) else "completed"
    if request.persist:
        try:
            await repository.store_raw_jobs(run_id, all_raw)
            await repository.upsert_jobs(jobs)
            await repository.update_discovery_run(run_id, status, counts["new"], len(jobs), errors, provider_results=[r.model_dump() for r in reports], metrics=metrics, rejections=rejections, duration_ms=round((time.monotonic() - started) * 1000))
        except Exception:
            await repository.update_discovery_run(run_id, "failed", 0, len(jobs), {"storage": "PERSISTENCE_ERROR"})
            raise
    logger.info(json.dumps({"run_id": run_id, "stage": "completed", "duration_ms": round((time.monotonic() - started) * 1000), "metrics": metrics}))
    return DiscoveryResponse(run_id=run_id, discovered=len(jobs), stored=counts["new"] if request.persist else 0, jobs=[j for j in merged if j.id in affected_ids], errors=errors, source_report=reports, metrics=metrics)
