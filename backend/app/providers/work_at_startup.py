from app.models import RawInternship, RemoteStatus, SourceName
from app.providers.base import Provider


class WorkAtAStartupProvider(Provider):
    source = SourceName.work_at_a_startup
    endpoint = "https://www.workatastartup.com/jobs"

    async def discover(self, query: str, limit: int) -> list[RawInternship]:
        async with self.client() as client:
            response = await client.get(self.endpoint, params={"query": query})
            response.raise_for_status()
            html = response.text

        # Work at a Startup changes frontend markup often, so this provider keeps
        # extraction intentionally shallow and isolated from the pipeline.
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        anchors = soup.select("a[href*='/jobs/']")
        jobs: list[RawInternship] = []
        seen: set[str] = set()
        for anchor in anchors:
            href = anchor.get("href")
            text = " ".join(anchor.get_text(" ", strip=True).split())
            if not href or not text:
                continue
            url = href if href.startswith("http") else f"https://www.workatastartup.com{href}"
            if url in seen:
                continue
            seen.add(url)
            title, company = self._derive_title_company(text)
            jobs.append(
                RawInternship(
                    source=self.source,
                    source_id=url,
                    title=title,
                    company_name=company,
                    url=url,
                    description=text,
                    company_description="Work at a Startup listing",
                    remote_status=RemoteStatus.unknown,
                    raw={"anchor_text": text},
                )
            )
            if len(jobs) >= limit:
                break
        return jobs

    def _derive_title_company(self, text: str) -> tuple[str, str]:
        parts = [part.strip() for part in text.split("  ") if part.strip()]
        if len(parts) >= 2:
            return parts[0], parts[1]
        return text[:120], "Startup company"

