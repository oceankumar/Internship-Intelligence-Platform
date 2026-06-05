from abc import ABC, abstractmethod

import httpx

from app.config import Settings
from app.models import RawInternship, SourceName


class Provider(ABC):
    source: SourceName

    def __init__(self, settings: Settings):
        self.settings = settings

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self.settings.request_timeout_seconds,
            headers={"User-Agent": self.settings.discovery_user_agent},
            follow_redirects=True,
        )

    @abstractmethod
    async def discover(self, query: str, limit: int) -> list[RawInternship]:
        raise NotImplementedError

