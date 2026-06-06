import asyncio
import logging

from app.config import Settings
from app.models import DiscoveryRequest, DiscoveryResponse, Job, SourceReport, CompensationStatus, RemoteStatus
from app.pipeline.filters import is_phase_one_candidate
from app.pipeline.normalizer import normalize_job
from app.pipeline.scorer import score_job
from app.pipeline.trust import apply_trust
from app.providers.registry import get_providers
from app.services.repository import Repository


async def run_discovery(settings: Settings, repository: Repository, request: DiscoveryRequest) -> DiscoveryResponse:
    run_id = await repository.create_discovery_run(request.query, request.limit_per_source)
    providers = get_providers(settings, request.sources)
    errors: dict[str, str] = {}
    normalized: list[Job] = []
    all_raw_jobs = []

    source_stats: dict[str, dict[str, int]] = {}
    for p in providers:
        source_stats[p.source.value] = {
            "raw": 0,
            "internships": 0,
            "paid": 0,
            "remote": 0
        }

    async def run_provider(provider):
        try:
            return provider.source.value, await provider.discover(request.query, request.limit_per_source)
        except Exception as exc:
            return provider.source.value, exc

    results = await asyncio.gather(*(run_provider(provider) for provider in providers))
    for source, result in results:
        if isinstance(result, Exception):
            errors[source] = str(result)
            continue
        all_raw_jobs.extend(result)
        source_stats[source]["raw"] = len(result)
        
        for raw in result:
            job = normalize_job(raw)
            if not is_phase_one_candidate(job):
                continue
            
            source_stats[source]["internships"] += 1
            if job.compensation_status == CompensationStatus.paid:
                source_stats[source]["paid"] += 1
            if job.remote_status == RemoteStatus.remote:
                source_stats[source]["remote"] += 1
                
            job = apply_trust(score_job(job))
            normalized.append(job)

    # Format and log report in console
    report_lines = [
        "",
        "==================================================================",
        "                    DISCOVERY RUN ANALYSIS REPORT                 ",
        "==================================================================",
        f"Query: '{request.query}'",
        f"Limit per source: {request.limit_per_source}",
        "------------------------------------------------------------------",
        f"{'Source':<24} | {'Raw Jobs':<8} | {'Interns':<8} | {'Paid':<6} | {'Remote':<6}",
        "------------------------------------------------------------------"
    ]
    
    source_reports = []
    for source, stats in source_stats.items():
        report_lines.append(
            f"{source:<24} | {stats['raw']:<8} | {stats['internships']:<8} | {stats['paid']:<6} | {stats['remote']:<6}"
        )
        source_reports.append(
            SourceReport(
                source=source,
                raw_jobs=stats["raw"],
                internships=stats["internships"],
                paid_internships=stats["paid"],
                remote_internships=stats["remote"]
            )
        )
        
    report_lines.append("------------------------------------------------------------------")
    total_raw = sum(s["raw"] for s in source_stats.values())
    total_interns = sum(s["internships"] for s in source_stats.values())
    total_paid = sum(s["paid"] for s in source_stats.values())
    total_remote = sum(s["remote"] for s in source_stats.values())
    
    report_lines.append(
        f"{'TOTAL':<24} | {total_raw:<8} | {total_interns:<8} | {total_paid:<6} | {total_remote:<6}"
    )
    report_lines.append("==================================================================")
    report_lines.append("")
    
    # Store raw jobs for audit and trace support
    if run_id and all_raw_jobs:
        await repository.store_raw_jobs(run_id, all_raw_jobs)

    stored_jobs = await repository.upsert_jobs(normalized) if request.persist else normalized

    # Database lifecycle report
    db_unique = len(stored_jobs)
    db_duplicates = sum(j.source_count - 1 for j in stored_jobs)
    db_total = db_unique + db_duplicates
    
    report_lines.append("")
    report_lines.append("------------------------------------------------------------------")
    report_lines.append("                  DATABASE DEDUPLICATION & LIFECYCLE              ")
    report_lines.append("------------------------------------------------------------------")
    report_lines.append(f"Total Records (Crawled + History):  {db_total}")
    report_lines.append(f"Unique Internships (Stored):        {db_unique}")
    report_lines.append(f"Duplicate Count (Merged):           {db_duplicates}")
    report_lines.append(f"Deduplication Rate:                 {(db_duplicates / db_total * 100 if db_total > 0 else 0):.2f}%")
    report_lines.append("==================================================================")
    report_lines.append("")

    logger = logging.getLogger("uvicorn")
    logger.info("\n".join(report_lines))

    # Update run status
    if run_id:
        status = "failed" if len(errors) == len(providers) and providers else "completed"
        await repository.update_discovery_run(
            run_id=run_id,
            status=status,
            stored_count=len(stored_jobs),
            discovered_count=len(normalized),
            errors=errors
        )

    return DiscoveryResponse(
        discovered=len(normalized),
        stored=len(stored_jobs),
        jobs=stored_jobs,
        errors=errors,
        source_report=source_reports
    )
