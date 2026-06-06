from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.config import Settings, get_settings
from app.models import DiscoveryRequest, DiscoveryResponse, HealthResponse, Job
from app.pipeline.runner import run_discovery
from app.services.exporter import jobs_to_csv, jobs_to_xlsx
from app.services.repository import Repository, make_repository

app = FastAPI(title="Internship Intelligence Platform", version="0.1.0")


def get_repository(settings: Settings = Depends(get_settings)) -> Repository:
    return make_repository(settings)


settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    import logging
    logger = logging.getLogger("uvicorn")
    settings = get_settings()
    logger.info(f"FastAPI starting up. Database type: {'Supabase' if settings.supabase_enabled else 'Local JSON'}")
    if not settings.supabase_enabled:
        logger.info(f"Canonical Database File Path: {settings.data_path}")


@app.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", storage="supabase" if settings.supabase_enabled else "local_json")


@app.get("/api/jobs", response_model=list[Job])
async def list_jobs(repository: Repository = Depends(get_repository)) -> list[Job]:
    return await repository.list_jobs()


@app.post("/api/discovery/run", response_model=DiscoveryResponse)
async def discover(
    request: DiscoveryRequest,
    settings: Settings = Depends(get_settings),
    repository: Repository = Depends(get_repository),
) -> DiscoveryResponse:
    return await run_discovery(settings, repository, request)


@app.get("/api/companies/suspicious")
async def suspicious_companies(repository: Repository = Depends(get_repository)):
    return await repository.suspicious_companies()


@app.get("/api/export.csv")
async def export_csv(repository: Repository = Depends(get_repository)) -> Response:
    jobs = await repository.list_jobs()
    return Response(
        content=jobs_to_csv(jobs),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=internships.csv"},
    )


@app.get("/api/export.xlsx")
async def export_xlsx(repository: Repository = Depends(get_repository)) -> Response:
    jobs = await repository.list_jobs()
    return Response(
        content=jobs_to_xlsx(jobs),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=internships.xlsx"},
    )

