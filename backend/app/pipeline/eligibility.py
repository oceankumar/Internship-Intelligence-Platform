import re

from app.models import CandidateProfile, Job


def evaluate_eligibility(job: Job, profile: CandidateProfile) -> Job:
    reasons, conflicts = [], []
    if job.minimum_experience_months is not None:
        if job.minimum_experience_months > profile.experience_months:
            conflicts.append(f"Requires {job.minimum_experience_months} months experience; profile has {profile.experience_months}")
        else:
            reasons.append("Experience requirement fits your profile")
    if job.graduation_years:
        if profile.graduation_year is None:
            reasons.append("Graduation year needed to check eligibility")
        elif profile.graduation_year not in job.graduation_years:
            conflicts.append("Graduation year is outside the stated range")
        else:
            reasons.append("Graduation year matches the stated range")
    location_text = f"{job.location or ''} {job.description}"
    if re.search(r"US.only|US citizens? only|must (?:reside|be based) in (?:the )?(?:US|United States)", location_text, re.I):
        if profile.country and profile.country not in {"US", "USA", "United States"}:
            conflicts.append("US location/work-authorization restriction requires review")
        else:
            reasons.append("US location/work authorization must be confirmed")
    if conflicts:
        job.eligibility_status, job.eligibility_score = "Likely Not Eligible", 20
    elif reasons and not any("needed" in r or "confirmed" in r for r in reasons):
        job.eligibility_status, job.eligibility_score = "Likely Eligible", 90
    else:
        job.eligibility_status, job.eligibility_score = "Unclear", 60
    job.eligibility_reasons = conflicts + reasons or ["The listing does not provide enough explicit eligibility requirements"]
    return job
