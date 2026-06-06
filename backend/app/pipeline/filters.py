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
    if SENIORITY_REGEX.search(title):
        return False
        
    # Check internship keywords with word boundaries
    if INTERN_REGEX.search(title):
        return True
        
    opportunity_phrases = [
        "internship opportunity",
        "internship role",
        "internship program",
        "paid internship",
        "student internship",
    ]
    return any(phrase in description for phrase in opportunity_phrases)


