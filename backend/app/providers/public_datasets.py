import re
from datetime import datetime
from bs4 import BeautifulSoup
import httpx

from app.models import RawInternship, RemoteStatus, SourceName
from app.providers.base import Provider


class PublicDatasetsProvider(Provider):
    source = SourceName.public_datasets

    async def discover(self, query: str, limit: int) -> list[RawInternship]:
        url = "https://raw.githubusercontent.com/deepanshu1422/List-Of-Open-Source-Internships-Programs/master/README.md"
        
        try:
            async with self.client() as client:
                response = await client.get(url)
                response.raise_for_status()
                content = response.text
        except Exception:
            self.warnings.append("Program catalog fetch failed")
            return []

        lines = content.split("\n")
        jobs: list[RawInternship] = []
        terms = [term.lower() for term in query.split() if len(term) > 2]
        
        for line in lines:
            if '|' not in line:
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 5:
                continue
            
            # Check for header/separator lines
            col1 = parts[1]
            if "name" in col1.lower() or "---" in col1:
                continue
                
            name_raw = parts[1]
            stipend_raw = parts[2]
            timeline_raw = parts[3] if len(parts) >= 5 else ""
            eligibility_raw = parts[4] if len(parts) >= 6 else ""
            
            # Parse program name and link
            name_soup = BeautifulSoup(name_raw, "html.parser")
            name_a = name_soup.find("a")
            name_text = name_soup.get_text(" ", strip=True)
            
            # If name has no direct link, check markdown link [Name](url)
            program_url = None
            if name_a:
                program_url = name_a.get("href")
            else:
                match_md = re.search(r"\[([^\]]+)\]\(([^\)]+)\)", name_raw)
                if match_md:
                    name_text = match_md.group(1)
                    program_url = match_md.group(2)
            
            if not program_url:
                continue
                
            # Smart term matching query filter
            searchable = f"{name_text} {stipend_raw} {timeline_raw} {eligibility_raw}".lower()
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
                
            # Determine remote and compensation
            remote_status = RemoteStatus.unknown
            
            stipend_lower = stipend_raw.lower()
            compensation = stipend_raw if any(x in stipend_lower for x in ["yes", "paid", "stipend", "prize", "reward", "$", "₹"]) else None
            
            jobs.append(
                RawInternship(
                    source=self.source,
                    source_id=program_url,
                    title=f"{name_text} Mentorship/Fellowship",
                    company_name=name_text,
                    url=program_url,
                    description=f"Open Source fellowship/mentorship opportunity: {name_text}. Timeline: {timeline_raw}. Eligibility: {eligibility_raw}.",
                    location=None,
                    remote_status=remote_status,
                    compensation=compensation,
                    date_posted=None,
                    raw={
                        "stipend": stipend_raw,
                        "timeline": timeline_raw,
                        "eligibility": eligibility_raw
                    }
                )
            )
            
            if len(jobs) >= limit:
                break
                
        return jobs
