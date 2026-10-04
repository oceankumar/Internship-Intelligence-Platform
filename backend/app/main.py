import asyncio
import logging
import secrets
import time
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from io import BytesIO

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from app.config import get_settings
from app.models import ApplicationUpdate, CandidateProfile, DiscoveryRequest, JobCorrection, SavedSearch
from app.pipeline.runner import run_discovery
from app.pipeline.scorer import score_job
from app.pipeline.normalizer import extract_skills, role_family
from app.services.exporter import jobs_to_csv, jobs_to_xlsx
from app.services.repository import make_repository
from app.services.search import Filters, filter_jobs, interpret_query, sort_jobs

settings = get_settings()
app = FastAPI(title="InternAI - Internship Intelligence Platform", version="1.0.0")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
origins = list(dict.fromkeys([settings.frontend_origin, "http://localhost:3000", "http://127.0.0.1:3000"]))
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Content-Type", "Authorization"], allow_credentials=False)


@lru_cache
def get_repository():
    return make_repository(get_settings())


@app.middleware("http")
async def access_boundary(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin and origin not in origins:
        return JSONResponse(status_code=403, content={"error": {"code": "ORIGIN_DENIED", "message": "Origin is not allowed", "recoverable": False}})
    if settings.public_demo_mode and request.method not in {"GET", "HEAD", "OPTIONS"}:
        return JSONResponse(status_code=403, content={"error": {"code": "DEMO_READ_ONLY", "message": "Public demo is read-only", "recoverable": False}})
    if request.url.path != "/health":
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        if settings.api_token:
            allowed = secrets.compare_digest(token, settings.api_token)
        else:
            allowed = settings.app_env == "local" and request.client and request.client.host in {"127.0.0.1", "::1", "testclient"}
        if not allowed:
            return JSONResponse(status_code=401, content={"error": {"code": "AUTH_REQUIRED", "message": "Private access required", "recoverable": False}})
    try:
        if int(request.headers.get("content-length", "0")) > settings.resume_max_bytes:
            return JSONResponse(status_code=413, content={"error": {"code": "UPLOAD_TOO_LARGE", "message": "Request exceeds 2 MB", "recoverable": True}})
    except ValueError:
        return JSONResponse(status_code=400, content={"error": {"code": "INVALID_LENGTH", "message": "Invalid request length"}})
    return await call_next(request)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logging.getLogger(__name__).error("request_failed type=%s path=%s", type(exc).__name__, request.url.path)
    return JSONResponse(status_code=500, content={"error": {"code": "REQUEST_FAILED", "message": "The request could not be completed. Please retry.", "recoverable": True}})


@app.exception_handler(HTTPException)
async def expected_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": f"HTTP_{exc.status_code}", "message": str(exc.detail), "recoverable": exc.status_code != 401}})


@app.get("/health")
async def health():
    return {"status": "ok", "storage": storage_mode(), "ai_enabled": settings.enable_ai_classification}


def storage_mode():
    return "public_snapshot" if settings.public_demo_mode else "supabase" if settings.supabase_enabled else "local_json"


@app.get("/api/runtime")
async def runtime(repository=Depends(get_repository)):
    return {"public_demo": settings.public_demo_mode, "storage": storage_mode(), "snapshot_at": repository.snapshot["snapshot_at"] if settings.public_demo_mode else None}


@app.get("/api/health")
async def api_health():
    return await health()


@app.get("/api/ready")
async def api_ready(repository=Depends(get_repository)):
    return await ready(repository)


@app.get("/ready")
async def ready(repository=Depends(get_repository)):
    try:
        await asyncio.wait_for(repository.get_state("profile", {}), timeout=5)
        await asyncio.wait_for(repository.list_jobs(), timeout=10)
    except Exception:
        raise HTTPException(503, "Repository is not ready")
    return {"status": "ready", "storage": storage_mode(), "ai_configured": bool(settings.enable_ai_classification and settings.ai_model)}


async def ranked(repository):
    profile = await repository.profile()
    return [score_job(j, profile) for j in await repository.list_jobs()]


@app.get("/api/jobs")
async def legacy_jobs(repository=Depends(get_repository)):
    return sort_jobs(filter_jobs(await ranked(repository), Filters()), "recommended")


@app.get("/api/internships")
async def internships(filters: Filters = Depends(), page: int = 1, limit: int = 20, sort: str = "recommended", repository=Depends(get_repository)):
    if page < 1 or not 1 <= limit <= 100:
        raise HTTPException(422, "page must be positive and limit must be 1-100")
    if sort == "stipend" and (not filters.currency or not filters.period):
        raise HTTPException(422, "Choose currency and pay period to compare stipends")
    jobs = sort_jobs(filter_jobs(await ranked(repository), filters), sort)
    interpretation = interpret_query(filters.q)
    return {"items": jobs[(page-1)*limit:page*limit], "total": len(jobs), "page": page, "limit": limit, "parsed_filters": interpretation["filters"], "unparsed_query": interpretation["unparsed"], "search_warnings": interpretation["warnings"]}


@app.get("/api/recommendations")
async def recommendations(repository=Depends(get_repository)):
    jobs = filter_jobs(await ranked(repository), Filters(recommended=True))
    return {"items": sort_jobs(jobs, "recommended")[:12], "total": len(jobs)}


@app.get("/api/internships/{job_id}")
async def detail(job_id: str, repository=Depends(get_repository)):
    job = next((j for j in await ranked(repository) if j.id == job_id), None)
    if not job:
        raise HTTPException(404, "Internship not found")
    return job


@app.patch("/api/internships/{job_id}")
@app.patch("/api/applications/{job_id}")
async def update_application(job_id: str, body: ApplicationUpdate, repository=Depends(get_repository)):
    changes = body.model_dump(mode="json", exclude_unset=True)
    if any(changes.get(k) is None for k in ("application_status", "favorite", "hidden", "notes", "contact") if k in changes):
        raise HTTPException(422, "Status, flags, notes and contact cannot be null")
    current = next((j for j in await repository.list_jobs() if j.id == job_id), None)
    if not current:
        raise HTTPException(404, "Internship not found")
    if body.application_status == "applied" and not current.applied_at and "applied_at" not in changes:
        changes["applied_at"] = datetime.now(timezone.utc).isoformat()
    job = await repository.patch_job(job_id, changes)
    return score_job(job, await repository.profile())


@app.patch("/api/internships/{job_id}/corrections")
async def correction(job_id: str, body: JobCorrection, repository=Depends(get_repository)):
    job = await detail(job_id, repository)
    changes = {} if body.reset else {**job.corrections, **body.model_dump(mode="json", exclude_none=True, exclude={"reset"})}
    updated = await repository.patch_job(job_id, {"corrections": changes})
    return score_job(updated, await repository.profile())


@app.get("/api/applications")
async def applications(repository=Depends(get_repository)):
    return [j for j in await ranked(repository) if j.application_status != "not_applied" or j.favorite]


@app.get("/api/profile")
async def profile(repository=Depends(get_repository)):
    return await repository.profile()


@app.put("/api/profile")
async def save_profile(body: CandidateProfile, repository=Depends(get_repository)):
    await repository.put_state("profile", body.model_dump())
    return body


@app.get("/api/searches")
async def saved_searches(repository=Depends(get_repository)):
    return await repository.get_state("searches", [])


@app.post("/api/searches")
async def save_search(body: SavedSearch, repository=Depends(get_repository)):
    try:
        Filters.model_validate(body.filters)
    except ValidationError:
        raise HTTPException(422, "Invalid search filters")
    searches = await repository.get_state("searches", [])
    searches = [s for s in searches if s["name"] != body.name] + [body.model_dump()]
    await repository.put_state("searches", searches[-30:])
    return searches[-30:]


@app.delete("/api/searches/{name}")
async def delete_search(name: str, repository=Depends(get_repository)):
    searches = [s for s in await repository.get_state("searches", []) if s["name"] != name]
    await repository.put_state("searches", searches)
    return searches


_discovery_lock = asyncio.Lock()
_last_run = 0.0


@app.post("/api/discovery/run")
async def discover(body: DiscoveryRequest, repository=Depends(get_repository)):
    global _last_run
    if _discovery_lock.locked() or time.monotonic() - _last_run < settings.discovery_cooldown_seconds:
        raise HTTPException(429, "Discovery is running or cooling down. Try again in a minute.")
    async with _discovery_lock:
        _last_run = time.monotonic()
        return await run_discovery(settings, repository, body)


@app.get("/api/discovery/runs")
async def runs(repository=Depends(get_repository)):
    return await repository.list_runs()


@app.get("/api/discovery/runs/{run_id}")
async def run_detail(run_id: str, repository=Depends(get_repository)):
    result = await repository.get_state("run:" + run_id)
    if not result:
        raise HTTPException(404, "Run not found")
    return result


@app.get("/api/providers/health")
async def provider_health(repository=Depends(get_repository)):
    from app.models import SourceName
    runs = await repository.list_runs()
    result = []
    for source in SourceName:
        reports = [(r, p) for r in runs for p in r.get("provider_results", []) if p["source"] == source.value]
        current = reports[0][1] if reports else {}
        result.append({
            "source": source.value, **current,
            "status": "disabled" if source.value not in settings.enabled_sources or source.value in {"wellfound", "work_at_a_startup"} else current.get("status", "unknown"),
            "last_success": next((r["completed_at"] for r, p in reports if p.get("fetch_success")), None),
            "last_useful_result": next((r["completed_at"] for r, p in reports if p.get("useful_records", 0) > 0), None),
            "last_failure": next((r["completed_at"] for r, p in reports if p["status"] == "failing"), None),
        })
    return result


@app.get("/api/analytics/market")
@app.get("/api/analytics/skills")
async def analytics(repository=Depends(get_repository)):
    jobs = await ranked(repository)
    visible = filter_jobs(jobs, Filters())
    count = lambda values: dict(Counter(values).most_common(15))
    return {
        "total": len(visible),
        "new_today": sum(j.is_new for j in visible),
        "apply_now": sum(j.application_priority == "Apply Now" for j in visible),
        "strong_matches": sum(j.application_priority == "Strong Match" for j in visible),
        "closing_soon": sum(j.urgency_score > 0 for j in visible),
        "applications": sum(j.application_status != "not_applied" for j in jobs),
        "roles": count(j.role_family for j in visible),
        "skills": count(s for j in visible for s in j.required_skills),
        "missing_skills": count(s for j in visible if j.match_score >= 60 for s in j.missing_skills),
        "remote": count(j.remote_status.value if hasattr(j.remote_status, "value") else j.remote_status for j in visible),
        "paid": count(j.compensation_status.value if hasattr(j.compensation_status, "value") else j.compensation_status for j in visible),
        "pipeline": count(j.application_status for j in jobs if j.application_status != "not_applied"),
        "companies": count(j.company.name for j in visible),
        "discovered": count(j.date_discovered.date().isoformat() for j in visible),
        "priorities": count(j.application_priority for j in visible),
        "quarantined": sum(j.risk_state in {"quarantined", "blocked"} for j in jobs),
        "confirmed_paid": sum(j.compensation_status == "paid" for j in visible),
        "india_compatible": sum(j.worldwide_remote or "India" in j.remote_countries or j.country == "India" for j in visible),
        "programs": sum(j.opportunity_type != "internship" for j in jobs),
    }


@app.get("/api/companies/suspicious")
async def suspicious(repository=Depends(get_repository)):
    return await repository.suspicious_companies()


@app.get("/api/listings/risky")
async def risky_listings(repository=Depends(get_repository)):
    return [j for j in await ranked(repository) if j.risk_state in {"quarantined", "blocked"}]


@app.get("/api/export.{format}")
async def export(format: str, filters: Filters = Depends(), sort: str = "recommended", repository=Depends(get_repository)):
    if sort == "stipend" and (not filters.currency or not filters.period):
        raise HTTPException(422, "Choose currency and pay period to compare stipends")
    jobs = sort_jobs(filter_jobs(await ranked(repository), filters), sort)
    if format == "csv":
        return Response(jobs_to_csv(jobs), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=internships.csv"})
    if format == "xlsx":
        return Response(jobs_to_xlsx(jobs), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=internships.xlsx"})
    raise HTTPException(404, "Unknown export format")


@app.post("/api/resume/analyze")
async def analyze_resume(request: Request):
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > settings.resume_max_bytes:
            raise HTTPException(413, "Resume must be smaller than 2 MB")
    try:
        if request.headers.get("content-type", "").startswith("application/pdf"):
            if not content.startswith(b"%PDF-"):
                raise ValueError("Invalid PDF signature")
            from app.services.resume_parser import extract_pdf
            text = await extract_pdf(bytes(content))
        elif request.headers.get("content-type", "").startswith("text/plain"):
            text = bytes(content).decode("utf-8")[:50000]
        else:
            raise HTTPException(415, "Upload a PDF or UTF-8 text file")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "Could not extract resume text")
    if not text.strip():
        raise HTTPException(422, "No text found. Scanned PDFs require OCR; upload text instead.")
    lines = text.splitlines()
    return {"skills": extract_skills(text.lower()), "education": [l[:300] for l in lines if any(w in l.lower() for w in ("b.tech", "bachelor", "university", "master"))][:5], "suggested_role": role_family(text[:5000]), "method": "deterministic", "stored": False}
