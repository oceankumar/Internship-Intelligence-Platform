import re
from datetime import datetime
from itertools import zip_longest

from app.models import RawInternship, RemoteStatus, SourceName
from app.providers.base import Provider


def parse_date(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else None
    except ValueError:
        return None


class StartupCareerPagesProvider(Provider):
    source = SourceName.startup_career_pages

    async def discover(self, query, limit):
        batches = []
        async with self.client() as client:
            for company in self.settings.greenhouse_boards:
                endpoint = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
                try:
                    response = await client.get(endpoint, params={"content": "true"})
                    response.raise_for_status()
                    rows = response.json().get("jobs", [])
                except Exception:
                    self.warnings.append(f"Greenhouse board {company}: fetch or parsing failed")
                    continue
                candidates = [j for j in rows if re.search(r"\b(intern|internship|co-op|coop|fellow|fellowship)\b", j.get("title", ""), re.I)]
                terms = [t for t in query.lower().split() if len(t) > 2 and t != "internship"]
                candidates = [j for j in candidates if not terms or any(t in f'{j.get("title", "")} {company}'.lower() for t in terms)]
                batches.append([(company, endpoint, j) for j in candidates[:limit]])
            selected = [item for group in zip_longest(*batches) for item in group if item][:limit]
            jobs = []
            for company, endpoint, listing in selected:
                j = dict(listing)
                if j.get("id"):
                    try:
                        detail = await client.get(endpoint + "/" + str(j["id"]), params={"pay_transparency": "true"})
                        detail.raise_for_status()
                        j.update(detail.json())
                    except Exception:
                        self.warnings.append(f"Greenhouse {company}: detail unavailable; retained listing")
                title, url = j.get("title", ""), j.get("absolute_url")
                if not url:
                    continue
                terms = [t for t in query.lower().split() if len(t) > 2 and t != "internship"]
                if terms and not any(t in f"{title} {company}".lower() for t in terms):
                    continue
                pay = None
                ranges = j.get("pay_input_ranges") or []
                if ranges:
                    r = ranges[0]
                    if r.get("min_cents") is not None and r.get("max_cents") is not None and r.get("currency_type"):
                        pay = f'{r["currency_type"]} {r["min_cents"]/100:g}-{r["max_cents"]/100:g}'
                location = (j.get("location") or {}).get("name")
                j["board"] = company
                j["application_state"] = "open"
                jobs.append(RawInternship(source=self.source,source_id=f'{company}:{j.get("id") or url}',title=title,company_name=j.get("company_name") or company.capitalize(),url=url,description=j.get("content") or "",location=location,remote_status=RemoteStatus.remote if "remote" in (location or "").lower() else RemoteStatus.unknown,compensation=pay,date_posted=parse_date(j.get("first_published")),deadline=parse_date(j.get("application_deadline")),raw=j))
            return jobs
