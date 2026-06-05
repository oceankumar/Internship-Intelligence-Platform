import asyncio

from app.config import Settings
from app.models import DiscoveryRequest, DiscoveryResponse, Job
from app.pipeline.filters import is_phase_one_candidate
from app.pipeline.normalizer import normalize_job
from app.pipeline.scorer import score_job
from app.pipeline.trust import apply_trust
from app.providers.registry import get_providers
from app.services.repository import Repository


async def run_discovery(settings: Settings, repository: Repository, request: DiscoveryRequest) -> DiscoveryResponse:
    providers = get_providers(settings, request.sources)
    errors: dict[str, str] = {}
    normalized: list[Job] = []

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
        for raw in result:
            job = normalize_job(raw)
            if not is_phase_one_candidate(job):
                continue
            job = apply_trust(score_job(job))
            normalized.append(job)

    stored_jobs = await repository.upsert_jobs(normalized) if request.persist else normalized
    return DiscoveryResponse(
        discovered=len(normalized),
        stored=len(stored_jobs),
        jobs=stored_jobs,
        errors=errors,
    )
