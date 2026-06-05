from app.models import RawInternship, RemoteStatus, SourceName
from app.providers.base import Provider


class WellfoundProvider(Provider):
    source = SourceName.wellfound
    endpoint = "https://wellfound.com/jobs"

    async def discover(self, query: str, limit: int) -> list[RawInternship]:
        async with self.client() as client:
            response = await client.get(self.endpoint, params={"q": query})
            response.raise_for_status()
            html = response.text

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
            url = href if href.startswith("http") else f"https://wellfound.com{href}"
            if url in seen:
                continue
            seen.add(url)
            jobs.append(
                RawInternship(
                    source=self.source,
                    source_id=url,
                    title=text[:140],
                    company_name="Wellfound company",
                    url=url,
                    description=text,
                    remote_status=RemoteStatus.unknown,
                    raw={"anchor_text": text},
                )
            )
            if len(jobs) >= limit:
                break
        return jobs

