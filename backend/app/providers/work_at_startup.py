from app.models import RawInternship, SourceName
from app.providers.base import Provider


class WorkAtAStartupProvider(Provider):
    source = SourceName.work_at_a_startup

    async def discover(self, query: str, limit: int) -> list[RawInternship]:
        raise RuntimeError("Disabled: use the public YC Jobs connector for this overlapping source")
