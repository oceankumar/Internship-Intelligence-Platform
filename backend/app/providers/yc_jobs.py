import json
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.models import RawInternship, RemoteStatus, SourceName
from app.pipeline.dedupe import canonical_domain
from app.providers.base import Provider


class YCJobsProvider(Provider):
    source = SourceName.yc_jobs
    endpoint = "https://www.ycombinator.com/jobs"

    async def discover(self, query: str, limit: int) -> list[RawInternship]:
        async with self.client() as client:
            response = await client.get(self.endpoint)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            node = soup.select_one("[data-page]")
            rows = json.loads(node["data-page"]).get("props", {}).get("jobPostings", []) if node else []
            if not rows:
                self.warnings.append("Structured jobPostings payload missing")
            jobs = []
            # Fetch details only for internship candidates; preserve structured metadata on failure.
            for row in rows:
                title = row.get("title", "")
                if not any(s in (title + " " + row.get("type", "")).lower() for s in ("intern", "co-op", "fellow")):
                    continue
                url = urljoin(self.endpoint, row.get("url", ""))
                if canonical_domain(url) != "ycombinator.com":
                    continue
                raw = RawInternship(source=self.source, source_id=str(row["id"]), title=title, company_name=row.get("companyName") or "Unknown company", url=url, company_description=row.get("companyOneLiner"), location=row.get("location"), compensation=row.get("salaryRange") or None, raw=row)
                try:
                    detail = await client.get(url)
                    detail.raise_for_status()
                    for tag in BeautifulSoup(detail.text, "html.parser").select('script[type="application/ld+json"]'):
                        payload = json.loads(tag.string or "{}")
                        items = payload if isinstance(payload, list) else payload.get("@graph", [payload])
                        data = next((d for d in items if d.get("@type") == "JobPosting"), None)
                        if not data:
                            continue
                        raw.description = data.get("description") or ""
                        raw.company_website = data.get("hiringOrganization", {}).get("sameAs")
                        if data.get("jobLocationType") == "TELECOMMUTE":
                            raw.remote_status = RemoteStatus.remote
                        if data.get("datePosted"):
                            raw.date_posted = datetime.fromisoformat(data["datePosted"].replace("Z", "+00:00"))
                        if data.get("validThrough"):
                            raw.deadline = datetime.fromisoformat(data["validThrough"].replace("Z", "+00:00"))
                        raw.raw["detail"] = data
                except Exception:
                    self.warnings.append("A YC detail page could not be parsed; retained listing metadata")
                jobs.append(raw)
                if len(jobs) >= limit:
                    break
            return jobs
