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
    "compensation",
    "source",
    "relevance_score",
    "trust_score",
    "suspicious",
    "required_skills",
    "date_posted",
    "date_discovered",
]


def jobs_to_csv(jobs: list[Job]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=HEADERS)
    writer.writeheader()
    for job in jobs:
        writer.writerow(_row(job))
    return buffer.getvalue()


def jobs_to_xlsx(jobs: list[Job]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Internships"
    sheet.append(HEADERS)
    for job in jobs:
        row = _row(job)
        sheet.append([row[header] for header in HEADERS])
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
        "compensation": job.compensation,
        "source": job.source.value,
        "relevance_score": job.relevance_score,
        "trust_score": job.company.trust_score,
        "suspicious": job.suspicious,
        "required_skills": ", ".join(job.required_skills),
        "date_posted": job.date_posted.isoformat() if job.date_posted else "",
        "date_discovered": job.date_discovered.isoformat(),
    }

