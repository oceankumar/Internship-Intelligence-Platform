import csv
from io import BytesIO, StringIO

from openpyxl import Workbook

from app.models import Job

HEADERS = [
    "company",
    "title",
    "url",
    "location",
    "remote_status",
    "compensation_status",
    "stipend",
    "source",
    "sources",
    "source_count",
    "relevance_score",
    "match_score",
    "opportunity_score",
    "eligibility",
    "deadline",
    "application_priority",
    "application_status",
    "days_since_seen",
    "trust_score",
    "suspicious",
    "required_skills",
    "date_posted",
    "date_discovered",
    "stipend_min", "stipend_max", "currency", "period", "matching_skills", "missing_skills",
    "trust_reasons", "risk_state", "risk_reasons", "fit_score", "evidence_confidence", "notes", "contact", "interview_at",
]


def jobs_to_csv(jobs: list[Job]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=HEADERS)
    writer.writeheader()
    for job in jobs:
        writer.writerow({k: safe_cell(v) for k, v in _row(job).items()})
    return buffer.getvalue()


def jobs_to_xlsx(jobs: list[Job]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Internships"
    sheet.append(HEADERS)
    for job in jobs:
        row = _row(job)
        sheet.append([safe_cell(row[header]) for header in HEADERS])
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for column in sheet.columns:
        width = min(48, max(12, max(len(str(cell.value or "")) for cell in column) + 2))
        sheet.column_dimensions[column[0].column_letter].width = width
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _row(job: Job) -> dict[str, str | int | bool | None]:
    return {
        "company": job.company.name,
        "title": job.title,
        "url": job.url,
        "location": job.location,
        "remote_status": job.remote_status.value,
        "compensation_status": job.compensation_status.value,
        "stipend": job.compensation,
        "source": job.source.value if hasattr(job.source, "value") else str(job.source),
        "sources": ", ".join(s.value if hasattr(s, "value") else str(s) for s in job.sources),
        "source_count": job.source_count,
        "relevance_score": job.relevance_score,
        "match_score": job.match_score,
        "opportunity_score": job.opportunity_score,
        "eligibility": job.eligibility_status,
        "deadline": job.deadline.isoformat() if job.deadline else "",
        "application_priority": job.application_priority,
        "application_status": job.application_status,
        "days_since_seen": job.days_since_seen,
        "trust_score": job.trust_score,
        "suspicious": job.suspicious,
        "required_skills": ", ".join(job.required_skills),
        "date_posted": job.date_posted.isoformat() if job.date_posted else "",
        "date_discovered": job.date_discovered.isoformat(),
        "stipend_min": job.stipend_min, "stipend_max": job.stipend_max,
        "currency": job.compensation_currency, "period": job.compensation_period,
        "matching_skills": ", ".join(job.matching_skills), "missing_skills": ", ".join(job.missing_skills),
        "trust_reasons": "; ".join(job.company.trust_reasons), "risk_state": job.risk_state,
        "risk_reasons": "; ".join(job.risk_reasons), "fit_score": job.fit_score,
        "evidence_confidence": job.evidence_confidence, "notes": job.notes, "contact": job.contact,
        "interview_at": job.interview_at.isoformat() if job.interview_at else "",
    }


def safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value
