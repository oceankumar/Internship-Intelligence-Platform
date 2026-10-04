import hashlib
import re
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.models import Job


def canonical_url(url: str) -> str:
    try:
        p = urlsplit(url.strip())
        query = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith("utm_") and k.lower() not in {"ref", "source", "referral"}]
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), urlencode(sorted(query)), ""))
    except ValueError:
        return url


def canonical_domain(url: str | None) -> str:
    try:
        return (urlsplit(url or "").hostname or "").removeprefix("www.").lower()
    except ValueError:
        return ""


def canonical_company(name: str) -> str:
    name = re.sub(r"\b(incorporated|inc|corp|ltd|llc|gmbh)\.?$", "", name.lower().strip())
    return " ".join(re.sub(r"[^\w\s]", " ", name).split())


def canonical_title(title: str) -> str:
    title = title.lower()
    for pat, replacement in [(r"\bswe\b", "software engineer"), (r"\bsoftware engineering\b", "software engineer"), (r"\binternship\b", "intern"), (r"front[ -]end", "frontend"), (r"back[ -]end", "backend"), (r"full[ -]stack", "fullstack")]:
        title = re.sub(pat, replacement, title)
    return " ".join(re.sub(r"[^\w\s]", " ", title).split())


def titles_are_similar(a: str, b: str) -> bool:
    return canonical_title(a) == canonical_title(b)


def job_fingerprint(job: Job) -> str:
    key = canonical_url(job.url)
    if not specific_url(key):
        key += '|' + '|'.join([job.source.value, job.source_id or '', canonical_title(job.title), job.location or ''])
    return hashlib.sha256(key.encode()).hexdigest()[:24]


def specific_url(url: str) -> bool:
    p = urlsplit(canonical_url(url))
    return bool(p.query) or p.path.lower().rstrip('/') not in {'', '/careers', '/jobs', '/career', '/join-us', '/careers/jobs'}


def identity_keys(job: Job) -> set[str]:
    keys = {'url:' + canonical_url(u) for u in [job.url, *job.original_urls] if specific_url(u)}
    for url in [job.url, *job.original_urls]:
        p = urlsplit(url)
        query = dict(parse_qsl(p.query))
        requisition = query.get('gh_jid')
        if canonical_domain(url) in {'boards.greenhouse.io', 'job-boards.greenhouse.io'}:
            match = re.search(r'/jobs/(\d+)', p.path)
            requisition = query.get('token') or (match[1] if match else requisition)
        if requisition and requisition.isdigit():
            keys.add('greenhouse:' + requisition)
    for instance in job.source_instances:
        value = instance.get('provider_job_id')
        if value and value != instance.get('canonical_apply_url'):
            keys.add('id:' + instance['provider'] + ':' + value)
    if job.source_id and job.source_id != job.url:
        keys.add('id:' + job.source.value + ':' + job.source_id)
    return keys


def company_fingerprint(name: str, website_url: str | None = None) -> str:
    return hashlib.sha256(canonical_company(name).encode()).hexdigest()[:24]


def same_job(a: Job, b: Job) -> bool:
    if identity_keys(a).intersection(identity_keys(b)):
        return True
    if a.source == b.source:
        return False
    if not specific_url(a.url) or not specific_url(b.url):
        return False
    hosts = {canonical_domain(a.url), canonical_domain(b.url)}
    if hosts.issubset({'boards.greenhouse.io', 'job-boards.greenhouse.io'}) or (len(hosts) == 1 and next(iter(hosts)) in {'jobs.lever.co', 'jobs.ashbyhq.com'}):
        return False
    if canonical_company(a.company.name) != canonical_company(b.company.name):
        return False
    if canonical_title(a.title) != canonical_title(b.title):
        return False
    if not a.location or not b.location or a.location.casefold() != b.location.casefold():
        return False
    # Different requisitions can have identical titles: require corroborating text.
    return min(len(a.description), len(b.description)) >= 160 and SequenceMatcher(None, a.description, b.description).ratio() >= 0.92


USER_FIELDS = ("application_status", "applied_at", "favorite", "hidden", "notes", "interview_at", "reminder_at", "contact", "corrections")


def merge_jobs(existing: list[Job], incoming: list[Job]) -> tuple[list[Job], dict[str, int]]:
    output = [j.model_copy(deep=True) for j in existing]
    indexes, groups = {}, {}
    def index(job, position):
        for key in identity_keys(job):
            indexes.setdefault(key, set()).add(position)
        groups.setdefault((canonical_company(job.company.name), canonical_title(job.title)), set()).add(position)
    for position, job in enumerate(output):
        index(job, position)
    metrics = {"new": 0, "updated": 0, "duplicates": 0}
    for item in incoming:
        candidates = set()
        for key in identity_keys(item):
            candidates.update(indexes.get(key, set()))
        candidates.update(groups.get((canonical_company(item.company.name), canonical_title(item.title)), set()))
        old_position = next((i for i in sorted(candidates) if same_job(output[i], item)), None)
        old = output[old_position] if old_position is not None else None
        fresh = item.model_copy(deep=True)
        fresh.id = old.id if old else (fresh.id or job_fingerprint(fresh))
        fresh.company.id = old.company.id if old else company_fingerprint(fresh.company.name)
        if old:
            metrics["duplicates"] += 1
            metrics["updated"] += 1
            if len(old.description) > len(fresh.description):
                fresh.description, fresh.summary = old.description, old.summary
                fresh.required_skills, fresh.preferred_skills = old.required_skills, old.preferred_skills
                fresh.mentioned_skills = old.mentioned_skills
            if not fresh.compensation:
                for key in ("compensation", "compensation_status", "stipend_min", "stipend_max", "compensation_currency", "compensation_period"):
                    setattr(fresh, key, getattr(old, key))
            if fresh.remote_status == 'unknown' and old.remote_status != 'unknown':
                fresh.remote_status = old.remote_status
            fresh.first_seen = old.first_seen
            fresh.date_discovered = old.date_discovered
            for key in ("date_posted", "deadline", "location"):
                if getattr(fresh, key) is None:
                    setattr(fresh, key, getattr(old, key))
            fresh.provenance = {**old.provenance, **fresh.provenance}
            if "source_values" in fresh.provenance:
                fresh.provenance["source_values"]["required_skills"] = fresh.required_skills
                fresh.provenance["source_values"]["compensation_status"] = fresh.compensation_status.value
                fresh.provenance["source_values"]["remote_status"] = fresh.remote_status.value
            if not fresh.company.website_url:
                fresh.company.website_url = old.company.website_url
            fresh.company.excluded = old.company.excluded or fresh.company.excluded
            for key in USER_FIELDS:
                setattr(fresh, key, getattr(old, key))
            fresh.sources = list(dict.fromkeys(old.sources + fresh.sources + [fresh.source]))
            fresh.original_urls = list(dict.fromkeys(old.original_urls + [old.url] + fresh.original_urls + [fresh.url]))
            fresh.url, fresh.source, fresh.source_id = old.url, old.source, old.source_id
            fresh.source_instances = list({tuple(sorted(v.items())): v for v in old.source_instances + fresh.source_instances}.values())
            output[old_position] = fresh
            index(fresh, old_position)
        else:
            metrics["new"] += 1
            fresh.sources = list(dict.fromkeys(fresh.sources + [fresh.source]))
            fresh.original_urls = list(dict.fromkeys(fresh.original_urls + [fresh.url]))
            output.append(fresh)
            index(fresh, len(output) - 1)
        fresh.source_count = len(fresh.sources)
    return output, metrics
