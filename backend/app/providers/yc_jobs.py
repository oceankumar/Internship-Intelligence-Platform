from bs4 import BeautifulSoup

from app.models import RawInternship, RemoteStatus, SourceName
from app.providers.base import Provider


class YCJobsProvider(Provider):
    source = SourceName.yc_jobs
    endpoint = "https://www.ycombinator.com/jobs"

    async def discover(self, query: str, limit: int) -> list[RawInternship]:
        async with self.client() as client:
            response = await client.get(self.endpoint, params={"query": query})
            response.raise_for_status()
            html = response.text

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("a[href*='/companies/'][href*='/jobs/']")
        jobs: list[RawInternship] = []
        seen: set[str] = set()
        for card in cards:
            href = card.get("href")
            if not href:
                continue
            url = href if href.startswith("http") else f"https://www.ycombinator.com{href}"
            if url in seen:
                continue
            seen.add(url)
            text = " ".join(card.get_text(" ", strip=True).split())
            if not text:
                continue
            title, company = self._split_title_company(text)
            jobs.append(
                RawInternship(
                    source=self.source,
                    source_id=url,
                    title=title,
                    company_name=company,
                    url=url,
                    description=text,
                    company_description="Y Combinator company listing",
                    remote_status=RemoteStatus.unknown,
                    raw={"card_text": text},
                )
            )
            if len(jobs) >= limit:
                break
        return jobs

    def _split_title_company(self, text: str) -> tuple[str, str]:
        separators = [" at ", " - ", " | "]
        for separator in separators:
            if separator in text:
                left, right = text.split(separator, 1)
                return left.strip() or "Software intern", right.strip() or "YC company"
        return text[:120], "YC company"

