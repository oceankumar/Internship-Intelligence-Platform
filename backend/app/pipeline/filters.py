from app.models import Job

SENIORITY_EXCLUSIONS = {
    "manager",
    "director",
    "head of",
    "lead ",
    "senior",
    "staff",
    "principal",
}


def is_phase_one_candidate(job: Job) -> bool:
    title = job.title.lower()
    description = job.description.lower()
    if "intern" in title:
        return True
    if any(term in title for term in SENIORITY_EXCLUSIONS):
        return False
    opportunity_phrases = [
        "internship opportunity",
        "internship role",
        "internship program",
        "paid internship",
        "student internship",
    ]
    return any(phrase in description for phrase in opportunity_phrases)

