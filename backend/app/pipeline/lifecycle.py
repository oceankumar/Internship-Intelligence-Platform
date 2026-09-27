from datetime import datetime, timezone

from app.config import get_settings
from app.models import Job


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def refresh_lifecycle(job: Job, now: datetime | None = None) -> Job:
    now = now or datetime.now(timezone.utc)
    first = utc(job.first_seen or job.date_discovered)
    last = utc(job.last_seen or job.date_discovered)
    age = max(0, (now - utc(job.date_posted or first)).days)
    unseen = max(0, (now - last).days)
    job.days_since_seen = unseen
    job.is_new = (now - first).total_seconds() < 86400
    job.expired = bool(job.deadline and utc(job.deadline) < now)
    job.stale = unseen >= get_settings().stale_days
    job.active = not (job.closed or job.expired or unseen >= get_settings().inactive_days)
    job.freshness_score = max(0, 100 - age * 3) if job.date_posted else max(0, 60 - age * 2)
    job.urgency_score = 100 if job.deadline and 0 <= (utc(job.deadline) - now).total_seconds() <= 7 * 86400 else 0
    if not job.active:
        job.freshness_score = 0
    return job
