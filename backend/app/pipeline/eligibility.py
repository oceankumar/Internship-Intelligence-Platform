import re

from app.models import CandidateProfile, Job
from app.pipeline.geography import canonical_country, REGIONS


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
    country = canonical_country(profile.country)
    if country and job.location and not job.country and not job.remote_countries and not job.worldwide_remote:
        reasons.append("Location/geography must be confirmed; country was not recognized")
    if job.country and country and job.country != country and not job.worldwide_remote and not job.remote_countries:
        reasons.append("Listed location is abroad; relocation and work authorization must be confirmed")
    if re.search(r'high school',job.title,re.I) and re.search(r'bachelor|b\.?tech|university|master',profile.education,re.I):
        conflicts.append("High-school internship does not align with stated university education")
    if job.remote_countries:
        if not country:
            reasons.append("Country needed to check remote geography")
        elif country not in job.remote_countries:
            label = ', '.join(job.remote_countries).replace('United States', 'United States (US)')
            conflicts.append(f"Remote/location restriction: {label} only; profile country is {country}")
        else:
            reasons.append("Candidate country matches stated location restriction")
    if job.remote_regions:
        if not country:
            reasons.append("Country needed to check regional restriction")
        elif not any(country in REGIONS[r] for r in job.remote_regions):
            reasons.append("Regional eligibility must be confirmed; region coverage is incomplete")
    if job.authorization_required:
        reasons.append("Work authorization/visa requirement must be confirmed; visa status is not inferred")
    if job.timezone_restriction:
        reasons.append("Timezone availability must be confirmed: " + job.timezone_restriction)
    if job.degree_requirement:
        if not profile.education:
            reasons.append("Education needed to check degree requirement")
        elif re.search(r"master|ph\.?d", job.degree_requirement, re.I) and not re.search(r"bachelor|undergraduate|b\.?tech", job.degree_requirement, re.I) and not re.search(r"master|ph\.?d", profile.education, re.I):
            conflicts.append("Stated postgraduate degree requirement does not match profile education")
        elif re.search(r"computer science|engineering|b\.?tech", profile.education, re.I):
            reasons.append("Profile education aligns with stated degree field")
        else:
            reasons.append("Degree equivalence must be confirmed")
    if conflicts:
        job.eligibility_status, job.eligibility_score = "Likely Not Eligible", 20
    elif reasons and not any("needed" in r or "confirmed" in r for r in reasons):
        job.eligibility_status, job.eligibility_score = "Likely Eligible", 90
    else:
        job.eligibility_status, job.eligibility_score = "Unclear", 60
    job.eligibility_reasons = conflicts + reasons or ["The listing does not provide enough explicit eligibility requirements"]
    return job
