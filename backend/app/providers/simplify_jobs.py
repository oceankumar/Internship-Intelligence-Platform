import re
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import httpx

from app.models import RawInternship, RemoteStatus, SourceName
from app.providers.base import Provider


class SimplifyJobsProvider(Provider):
    source = SourceName.simplify_jobs

    async def discover(self, query: str, limit: int) -> list[RawInternship]:
        url = "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md"
        
        async with self.client() as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.text

        soup = BeautifulSoup(content, "html.parser")
        rows = soup.select("tbody tr")
        
        # Smart query matching
        terms = [term.lower() for term in query.split() if len(term) > 2]
        
        jobs: list[RawInternship] = []
        last_company_name = "Unknown Company"
        last_company_url = None
        
        for row in rows:
            tds = row.find_all("td")
            if len(tds) < 5:
                continue
            
            # 1. Parse Company cell
            company_cell = tds[0]
            company_a = company_cell.find("a")
            company_text = company_cell.get_text(" ", strip=True)
            
            is_sub_role = "↳" in company_text or company_text.strip() == "↳"
            
            if is_sub_role:
                company_name = last_company_name
                company_website = last_company_url
            else:
                company_name = company_text.replace("🔥", "").strip()
                company_website = company_a.get("href") if company_a else None
                if company_name:
                    last_company_name = company_name
                    last_company_url = company_website
            
            # 2. Parse Role cell
            role_text = tds[1].get_text(" ", strip=True)
            
            # 3. Parse Location cell
            location_text = tds[2].get_text(" ", strip=True)
            
            # 4. Parse Application Link cell
            link_cell = tds[3]
            link_a = link_cell.find("a")
            job_url = link_a.get("href") if link_a else None
            
            # 5. Parse Age cell
            age_text = tds[4].get_text(" ", strip=True)
            
            # Filter closed jobs
            link_html = str(link_cell)
            if "🔒" in link_html or "closed" in link_html.lower() or "🔒" in company_text or "🔒" in age_text:
                continue
            if not job_url:
                continue
                
            # Clean job URL
            from app.pipeline.dedupe import canonical_url
            job_url = canonical_url(job_url)
            
            # Smart term matching query filter
            searchable = f"{company_name} {role_text} {location_text}".lower()
            matched = False
            if not terms:
                matched = True
            else:
                for term in terms:
                    if term == "internship" and ("intern" in searchable or "co-op" in searchable or "coop" in searchable or "fellow" in searchable):
                        matched = True
                        break
                    if term in searchable:
                        matched = True
                        break
            
            if not matched:
                continue
                
            # Parse date posted
            date_posted = self._parse_relative_age(age_text)
            
            jobs.append(
                RawInternship(
                    source=self.source,
                    source_id=job_url,
                    title=role_text,
                    company_name=company_name,
                    url=job_url,
                    description=f"Internship role at {company_name}. Location: {location_text}. Posted {age_text} ago.",
                    company_website=company_website,
                    location=location_text,
                    remote_status=RemoteStatus.unknown,
                    compensation=None,
                    date_posted=date_posted,
                    raw={
                        "category": "Tech",
                        "age": age_text,
                        "location_text": location_text
                    }
                )
            )
            
            if len(jobs) >= limit:
                break
                
        return jobs

    def _parse_relative_age(self, age_str: str) -> datetime | None:
        now = datetime.now(timezone.utc)
        match = re.match(r"^(\d+)\s*d$", age_str, re.IGNORECASE)
        if match:
            days = int(match.group(1))
            return now - timedelta(days=days)
        return None
