import asyncio
import json
from datetime import datetime
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
        links_data: list[tuple[str, str]] = []
        seen: set[str] = set()

        for card in cards:
            href = card.get("href")
            if not href:
                continue
            url = href if href.startswith("http") else f"https://www.ycombinator.com{href}"
            if url in seen:
                continue
            seen.add(url)
            card_text = " ".join(card.get_text(" ", strip=True).split())
            links_data.append((url, card_text))

        # Limit candidate links to discover
        links_data = links_data[:limit]

        async def fetch_and_parse_details(url: str, card_text: str) -> RawInternship:
            try:
                async with self.client() as detail_client:
                    r = await detail_client.get(url)
                    if r.status_code == 200:
                        s = BeautifulSoup(r.text, "html.parser")
                        tag = s.find("script", type="application/ld+json")
                        if tag and tag.string:
                            data = json.loads(tag.string)
                            title = data.get("title") or self._split_title_company(card_text)[0]
                            company_name = data.get("hiringOrganization", {}).get("name") or self._split_title_company(card_text)[1]
                            description = data.get("description") or card_text
                            company_website = data.get("hiringOrganization", {}).get("sameAs")
                            
                            # Parse locations
                            locations = []
                            job_locs = data.get("jobLocation", [])
                            if isinstance(job_locs, dict):
                                job_locs = [job_locs]
                            for loc in job_locs:
                                addr = loc.get("address", {})
                                parts = []
                                if addr.get("addressLocality"):
                                    parts.append(addr.get("addressLocality"))
                                if addr.get("addressRegion"):
                                    parts.append(addr.get("addressRegion"))
                                if addr.get("addressCountry"):
                                    parts.append(addr.get("addressCountry"))
                                if parts:
                                    locations.append(", ".join(parts))
                            location_str = " / ".join(locations) if locations else None
                            
                            # Parse salary
                            salary = data.get("baseSalary", {})
                            salary_str = None
                            if salary:
                                curr = salary.get("currency", "")
                                val = salary.get("value", {})
                                if isinstance(val, dict):
                                    min_val = val.get("minValue")
                                    max_val = val.get("maxValue")
                                    unit = val.get("unitText", "")
                                    if min_val and max_val:
                                        salary_str = f"{min_val} - {max_val} {curr}"
                                        if unit:
                                            salary_str += f" per {unit}"
                                    elif min_val:
                                        salary_str = f"{min_val} {curr}"
                                        if unit:
                                            salary_str += f" per {unit}"
                            
                            date_posted = None
                            date_str = data.get("datePosted")
                            if date_str:
                                try:
                                    date_posted = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                                except ValueError:
                                    pass

                            return RawInternship(
                                source=self.source,
                                source_id=url,
                                title=title,
                                company_name=company_name,
                                url=url,
                                description=description,
                                company_description="Y Combinator structured job listing",
                                company_website=company_website,
                                location=location_str,
                                remote_status=RemoteStatus.unknown,
                                compensation=salary_str,
                                date_posted=date_posted,
                                raw=data,
                            )
            except Exception:
                pass

            # Fallback to old behavior if anything fails
            title, company = self._split_title_company(card_text)
            return RawInternship(
                source=self.source,
                source_id=url,
                title=title,
                company_name=company,
                url=url,
                description=card_text,
                company_description="Y Combinator company listing",
                remote_status=RemoteStatus.unknown,
                raw={"card_text": card_text},
            )

        if not links_data:
            return []

        tasks = [fetch_and_parse_details(url, text) for url, text in links_data]
        return list(await asyncio.gather(*tasks))

    def _split_title_company(self, text: str) -> tuple[str, str]:
        separators = [" at ", " - ", " | "]
        for separator in separators:
            if separator in text:
                left, right = text.split(separator, 1)
                return left.strip() or "Software intern", right.strip() or "YC company"
        return text[:120], "YC company"


