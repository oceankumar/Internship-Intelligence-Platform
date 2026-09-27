import re
from datetime import datetime
import json
import httpx

from app.models import RawInternship, RemoteStatus, SourceName
from app.providers.base import Provider


class StartupCareerPagesProvider(Provider):
    source = SourceName.startup_career_pages

    async def discover(self, query: str, limit: int) -> list[RawInternship]:
        companies = self.settings.greenhouse_boards
        
        jobs: list[RawInternship] = []
        terms = [term.lower() for term in query.split() if len(term) > 2]
        
        for company in companies:
            url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
            try:
                async with self.client() as client:
                    response = await client.get(url, params={"content": "true"})
                    response.raise_for_status()
                    data = response.json()
            except Exception:
                self.warnings.append(f"Greenhouse board {company}: fetch or parsing failed")
                continue
                
            jobs_list = data.get("jobs", [])
            for j in jobs_list:
                title = j.get("title", "")
                title_lower = title.lower()
                
                is_internship = bool(re.search(r"\b(intern|internship|co-op|coop|fellow|fellowship)\b", title_lower))
                if not is_internship:
                    continue
                    
                location_name = j.get("location", {}).get("name", "Unknown Location")
                job_url = j.get("absolute_url")
                if not job_url:
                    continue
                    
                # Clean job URL
                from app.pipeline.dedupe import canonical_url
                job_url = canonical_url(job_url)
                
                # Fetch metadata to extract date
                updated_at_str = j.get("updated_at")
                date_posted = None
                if updated_at_str:
                    try:
                        date_posted = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                    except ValueError:
                        pass
                
                # Smart term matching query filter
                searchable = f"{company} {title} {location_name}".lower()
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
                    
                # Determine remote status
                loc_lower = location_name.lower()
                remote_status = RemoteStatus.unknown
                if "remote" in loc_lower or "remote" in title_lower:
                    remote_status = RemoteStatus.remote
                    
                jobs.append(
                    RawInternship(
                        source=self.source,
                        source_id=job_url,
                        title=title,
                        company_name=company.capitalize(),
                        url=job_url,
                        description=j.get("content") or "",
                        location=location_name,
                        remote_status=remote_status,
                        compensation=None,
                        date_posted=None,
                        raw=j
                    )
                )
                
                if len(jobs) >= limit:
                    break
                    
            if len(jobs) >= limit:
                break
                
        return jobs
