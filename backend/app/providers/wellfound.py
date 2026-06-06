from app.models import RawInternship, RemoteStatus, SourceName
from app.providers.base import Provider


class WellfoundProvider(Provider):
    source = SourceName.wellfound
    endpoint = "https://wellfound.com/jobs"

    async def discover(self, query: str, limit: int) -> list[RawInternship]:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            "Wellfound provider is marked as UNSUPPORTED in Phase 1.5 due to DataDome anti-bot restrictions. "
            "Please use alternative sources such as SimplifyJobs, Google Jobs API, or LinkedIn search scrapers."
        )
        return []


