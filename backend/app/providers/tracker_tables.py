import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.models import RawInternship
from app.pipeline.dedupe import canonical_url

ALIASES = {"company": ["company", "organization"], "title": ["role", "position", "job title"], "location": ["location"], "url": ["application", "link", "apply", "posting"], "age": ["age", "date", "posted"], "pay": ["salary", "stipend", "compensation"]}


def date_value(value):
    now = datetime.now(timezone.utc)
    relative = re.fullmatch(r"(\d+)\s*d", value.strip(), re.I)
    if relative:
        return now - timedelta(days=int(relative[1]))
    for fmt in ("%b %d, %Y", "%b %d %Y", "%Y-%m-%d", "%b %d", "%B %d"):
        try:
            result = datetime.strptime(value.strip() if "%Y" in fmt else value.strip() + f" {now.year}", fmt if "%Y" in fmt else fmt + " %Y")
            if "%Y" not in fmt:
                result = result.replace(year=now.year)
                if result.replace(tzinfo=timezone.utc) > now:
                    result = result.replace(year=now.year - 1)
            return result.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def cell(value):
    soup = BeautifulSoup(value, "html.parser")
    link = soup.find("a", href=True)
    md = re.search(r"\[([^\]]+)\]\(([^)]+)\)", value)
    return (md[1] if md else soup.get_text(" ", strip=True)), (link["href"] if link else md[2] if md else None)


def parse_tracker(content, tracker_url, source, query, limit, warnings):
    soup = BeautifulSoup(content, "html.parser")
    tables = []
    for table in soup.find_all("table"):
        tables.append([[str(c) for c in row.find_all(["td", "th"])] for row in table.find_all("tr")])
    markdown = []
    for line in content.splitlines():
        if line.strip().startswith("|"):
            markdown.append([s.strip() for s in line.strip().strip("|").split("|")])
    if markdown:
        tables.append(markdown)
    jobs, seen = [], set()
    for rows in tables:
        mapping, last_company, last_website = {}, "Unknown company", None
        for row in rows:
            texts = [cell(v)[0] for v in row]
            candidate = {key: next((i for i, name in enumerate(texts) if any(alias in name.lower() for alias in aliases)), -1) for key, aliases in ALIASES.items()}
            if candidate['company'] >= 0 and candidate['title'] >= 0 and candidate['url'] >= 0:
                mapping = candidate
                continue
            if len(row) < (3 if mapping else 5) or all(re.fullmatch(r"[: -]+", t or "-") for t in texts):
                continue
            columns = mapping or {"company": 0, "title": 1, "location": 2, "url": 3, "age": 4}
            if any(columns[k] >= len(row) for k in ("company", "title", "url")):
                continue
            def get(key):
                i = columns.get(key, -1)
                return cell(row[i]) if 0 <= i < len(row) else ("", None)
            company, website = get('company')
            if '\u21b3' in company:
                company, website = last_company, last_website
            else:
                company = company.replace('\U0001f525', '').strip()
                last_company, last_website = company, website
            title, _ = get('title')
            location, _ = get('location')
            age, _ = get('age')
            pay, _ = get('pay')
            _, url = get('url')
            if not url or re.search(r"closed|\U0001f512", ' '.join(row), re.I):
                continue
            if not re.search(r"\b(?:intern|internship|co-op|coop|fellow|fellowship)\b", title, re.I):
                continue
            searchable = f'{company} {title} {location}'.lower()
            terms = [t for t in query.lower().split() if len(t) > 2 and t != 'internship']
            if terms and not any(t in searchable for t in terms):
                continue
            url = canonical_url(urljoin(tracker_url, url))
            if url in seen:
                continue
            seen.add(url)
            jobs.append(RawInternship(source=source,source_id=url,title=title,company_name=company,url=url,location=location or None,company_website=website,compensation=pay or None,description=f"Community tracker lists {title} at {company}. Employer requirements have not been fetched.",date_posted=date_value(age),raw={"tracker_url":tracker_url,"age":age,"application_state":"unknown"}))
            if len(jobs) >= limit:
                return jobs
    if not tables:
        warnings.append("PARSER_DRIFT: no recognized HTML/Markdown table")
    elif not jobs:
        warnings.append("LOW_YIELD: no open internship rows matched")
    return jobs
