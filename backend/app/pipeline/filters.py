import re
from app.models import Job

INTERN_REGEX = re.compile(
    r"\b(intern|internship|co-op|coop|fellow|fellowship|apprentice|apprenticeship|student)\b",
    re.IGNORECASE
)

SENIORITY_REGEX = re.compile(
    r"\b(senior|staff|principal|lead|manager|director|head|vp|president|exec|executive|architect|chief|lead-|sr-|sr\.)\b",
    re.IGNORECASE
)


def is_phase_one_candidate(job: Job) -> bool:
    title = job.title.lower()
    description = job.description.lower()
    
    # Check seniority / exclusions first
    if SENIORITY_REGEX.search(title) and not re.search(r"\b(?:product|project) manager intern\b", title):
        return False
        
    # Check internship keywords with word boundaries
    if INTERN_REGEX.search(title):
        return True
    if job.provenance.get("explicit_internship"):
        return True
        
    opportunity_phrases = [
        "internship opportunity",
        "internship role",
        "internship program",
        "paid internship",
        "student internship",
    ]
    return any(phrase in description for phrase in opportunity_phrases)


def rejection_reason(job: Job) -> str | None:
    from app.pipeline.urls import safe_public_url
    if not safe_public_url(job.url):
        return "REJECTED_INVALID_URL"
    if SENIORITY_REGEX.search(job.title) and not re.search(r"\b(?:product|project) manager intern\b", job.title, re.I):
        return "REJECTED_SENIOR_ROLE"
    if not is_phase_one_candidate(job):
        return "REJECTED_NOT_INTERNSHIP"
    if job.company.excluded:
        return "REJECTED_EXCLUDED_COMPANY"
    return None
