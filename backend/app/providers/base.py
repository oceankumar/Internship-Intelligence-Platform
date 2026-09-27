from abc import ABC, abstractmethod
import asyncio
import time
from urllib.parse import urlsplit

import httpx

from app.config import Settings
from app.models import RawInternship, SourceName


class PoliteClient(httpx.AsyncClient):
    cache: dict[str, tuple[float, httpx.Response]] = {}
    last_request: dict[str, float] = {}
    host_locks: dict[str, asyncio.Lock] = {}

    def __init__(self, settings: Settings, warnings: list[str]):
        super().__init__(timeout=settings.request_timeout_seconds, headers={"User-Agent": settings.discovery_user_agent}, follow_redirects=True, max_redirects=3)
        self.settings = settings
        self.warnings = warnings

    async def get(self, url, **kwargs):
        key = str(url) + str(kwargs.get("params", ""))
        host = urlsplit(str(url)).hostname or ""
        lock = self.host_locks.setdefault(host, asyncio.Lock())
        async with lock:
            cached = self.cache.get(key)
            if cached and cached[0] > time.monotonic():
                return cached[1]
            delay = self.settings.provider_request_interval - (time.monotonic() - self.last_request.get(host, 0))
            if delay > 0:
                await asyncio.sleep(delay)
            for attempt in range(2):
                self.last_request[host] = time.monotonic()
                response = await super().get(url, **kwargs)
                if response.status_code not in {429, 502, 503, 504} or attempt:
                    break
                retry = response.headers.get("retry-after", "2")
                if not retry.isdigit() or int(retry) > 5:
                    break
                await asyncio.sleep(max(1, int(retry)))
            if response.is_success:
                if len(self.cache) >= 500:
                    self.cache.clear()
                self.cache[key] = (time.monotonic() + self.settings.provider_cache_seconds, response)
            else:
                self.warnings.append(f"{host}: HTTP {response.status_code}")
            return response


class Provider(ABC):
    source: SourceName

    def __init__(self, settings: Settings):
        self.settings = settings
        self.warnings: list[str] = []

    def client(self) -> httpx.AsyncClient:
        return PoliteClient(self.settings, self.warnings)

    @abstractmethod
    async def discover(self, query: str, limit: int) -> list[RawInternship]:
        raise NotImplementedError
