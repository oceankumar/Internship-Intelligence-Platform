from app.models import RawInternship, SourceName
from app.providers.base import Provider


class WellfoundProvider(Provider):
    source = SourceName.wellfound

    async def discover(self, query: str, limit: int) -> list[RawInternship]:
        raise RuntimeError("Disabled: automated public access is restricted")

