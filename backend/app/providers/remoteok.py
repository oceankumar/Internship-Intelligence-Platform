from datetime import datetime
import re
from typing import Any

from app.models import RawInternship, RemoteStatus, SourceName
from app.providers.base import Provider


class RemoteOKProvider(Provider):
    source = SourceName.remoteok
    endpoint = "https://remoteok.com/api"

    async def discover(self, query: str, limit: int) -> list[RawInternship]:
        terms = [term.lower() for term in query.split() if len(term) > 2]
        async with self.client() as client:
            response = await client.get(self.endpoint)
            response.raise_for_status()
            payload: list[dict[str, Any]] = response.json()

        jobs: list[RawInternship] = []
        for item in payload:
            if not isinstance(item, dict) or "position" not in item:
                continue
            title = str(item.get("position") or "")
            description = str(item.get("description") or "")
            tags = " ".join(item.get("tags") or [])
            searchable = f"{title} {description} {tags}".lower()
            if not re.search(r"\b(intern|internship|co-op|fellowship)\b", searchable):
                continue
            if terms and not any(term in searchable for term in terms):
                continue
            posted = self._parse_date(item.get("date"))
            company = str(item.get("company") or "Unknown company")
            slug = item.get("slug") or item.get("id") or title
            jobs.append(
                RawInternship(
                    source=self.source,
                    source_id=str(item.get("id") or slug),
                    title=title,
                    company_name=company,
                    url=str(item.get("url") or f"https://remoteok.com/remote-jobs/{slug}"),
                    description=description,
                    company_website=item.get("company_website"),
                    location=item.get("location"),
                    remote_status=RemoteStatus.remote,
                    compensation=str(item["salary"]) if item.get("salary") else None,
                    date_posted=posted,
                    raw=item,
                )
            )
            if len(jobs) >= limit:
                break
        return jobs

    def _parse_date(self, value: Any) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
