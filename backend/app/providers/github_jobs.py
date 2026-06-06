import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import httpx

from app.models import RawInternship, RemoteStatus, SourceName
from app.providers.base import Provider


class GitHubJobsProvider(Provider):
    source = SourceName.github_jobs

    async def discover(self, query: str, limit: int) -> list[RawInternship]:
        urls = [
            ("speedyapply_us", "https://raw.githubusercontent.com/speedyapply/2026-SWE-College-Jobs/main/README.md"),
            ("speedyapply_intl", "https://raw.githubusercontent.com/speedyapply/2026-SWE-College-Jobs/main/INTERN_INTL.md"),
            ("vansh_us", "https://raw.githubusercontent.com/vanshb03/Summer2026-Internships/main/README.md")
        ]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        jobs: list[RawInternship] = []
        terms = [term.lower() for term in query.split() if len(term) > 2]
        
        for key, url in urls:
            try:
                async with self.client() as client:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    content = response.text
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to fetch {url}: {e}")
                continue

            lines = content.split("\n")
            last_company_name = "Unknown Company"
            last_company_url = None
            
            for line in lines:
                if '|' not in line:
                    continue
                parts = [p.strip() for p in line.split('|')]
                if len(parts) < 6:
                    continue
                
                # Check for header/separator lines
                col1 = parts[1]
                if "company" in col1.lower() or "---" in col1:
                    continue
                
                # Parse columns: Company | Role/Position | Location | Link | Age/Date
                company_raw = parts[1]
                role_raw = parts[2]
                location_raw = parts[3]
                link_raw = parts[4]
                age_raw = parts[5] if len(parts) >= 7 else ""
                
                # Skip closed roles
                if "🔒" in link_raw or "closed" in link_raw.lower() or "🔒" in company_raw or "🔒" in age_raw:
                    continue
                
                # Parse company name and website from company cell (often contains HTML <a> or <strong>)
                company_soup = BeautifulSoup(company_raw, "html.parser")
                company_a = company_soup.find("a")
                company_text = company_soup.get_text(" ", strip=True)
                
                is_sub = "↳" in company_text or company_text.strip() == "↳"
                if is_sub:
                    company_name = last_company_name
                    company_website = last_company_url
                else:
                    company_name = company_text.strip()
                    company_website = company_a.get("href") if company_a else None
                    if company_name:
                        last_company_name = company_name
                        last_company_url = company_website
                
                # Clean role and location
                role_soup = BeautifulSoup(role_raw, "html.parser")
                role_text = role_soup.get_text(" ", strip=True)
                
                location_soup = BeautifulSoup(location_raw, "html.parser")
                location_text = location_soup.get_text(" ", strip=True)
                
                # Parse link
                link_soup = BeautifulSoup(link_raw, "html.parser")
                link_a = link_soup.find("a")
                job_url = link_a.get("href") if link_a else None
                if not job_url:
                    # Fallback regex for md link [Apply](url)
                    match_url = re.search(r"href=\"([^\"]+)\"", link_raw)
                    if match_url:
                        job_url = match_url.group(1)
                    else:
                        match_md = re.search(r"\]\(([^\)]+)\)", link_raw)
                        if match_md:
                            job_url = match_md.group(1)
                
                if not job_url:
                    continue
                
                # Clean job URL
                job_url = job_url.split("?")[0].split("&")[0]
                
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
                date_posted = self._parse_date_string(age_raw)
                
                jobs.append(
                    RawInternship(
                        source=self.source,
                        source_id=job_url,
                        title=role_text,
                        company_name=company_name,
                        url=job_url,
                        description=f"Internship at {company_name}. Location: {location_text}. Source: {key}.",
                        company_website=company_website,
                        location=location_text,
                        remote_status=RemoteStatus.unknown,
                        compensation="Paid stipend", # Default to paid for community-curated listings
                        date_posted=date_posted,
                        raw={
                            "sub_source": key,
                            "location_text": location_text,
                            "age": age_raw
                        }
                    )
                )
                
                if len(jobs) >= limit:
                    break
            
            if len(jobs) >= limit:
                break
                
        return jobs

    def _parse_date_string(self, val_str: str) -> datetime:
        now = datetime.utcnow()
        val_str = val_str.strip()
        if not val_str:
            return now
            
        # Match "1d", "2d", etc.
        match_days = re.match(r"^(\d+)\s*d$", val_str, re.IGNORECASE)
        if match_days:
            days = int(match_days.group(1))
            return now - timedelta(days=days)
            
        # Match "Month Day" like "May 09", "Apr 20"
        months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        match_date = re.match(r"^([a-z]+)\s*(\d+)$", val_str, re.IGNORECASE)
        if match_date:
            month_name = match_date.group(1).lower()[:3]
            day = int(match_date.group(2))
            if month_name in months:
                month_idx = months.index(month_name) + 1
                try:
                    dt = datetime(now.year, month_idx, day)
                    if dt > now:
                        dt = datetime(now.year - 1, month_idx, day)
                    return dt
                except ValueError:
                    pass
        return now
