from app.models import CandidateProfile, CompensationStatus, Job, RemoteStatus
from app.pipeline.eligibility import evaluate_eligibility
from app.pipeline.lifecycle import refresh_lifecycle
from app.pipeline.normalizer import enrich_fields, extract_skills, experience_months
from app.pipeline.trust import apply_trust

MATCH_WEIGHTS = {"skills": 40, "role": 25, "experience": 15, "remote": 10, "compensation": 10}
OPPORTUNITY_WEIGHTS = {"match": 45, "eligibility": 20, "trust": 15, "freshness": 15, "urgency": 5}


def extract_experience_years(text: str) -> int | None:
    months = experience_months(text)
    return months // 12 if months is not None else None


def score_job(job: Job, profile: CandidateProfile | None = None) -> Job:
    profile = profile or CandidateProfile()
    enrich_fields(job)
    for key, value in job.corrections.items():
        if key in {"remote_status", "compensation_status", "required_skills"}:
            if key == "remote_status":
                value = RemoteStatus(value)
            elif key == "compensation_status":
                value = CompensationStatus(value)
            setattr(job, key, value)
    apply_trust(job)
    refresh_lifecycle(job)
    evaluate_eligibility(job, profile)
    skills = set(s.casefold() for s in profile.skills)
    skills.update(extract_skills(" ".join(profile.skills).lower()))
    required = set(s.casefold() for s in job.required_skills)
    job.matching_skills = sorted(required & skills)
    job.missing_skills = sorted(required - skills)
    factors = {
        "skills": len(required & skills) / len(required) if required and skills else 0.4,
        "role": 1 if job.role_family in profile.preferred_roles else 0.3,
        "experience": 0.6 if job.minimum_experience_months is None else 1 if job.minimum_experience_months <= profile.experience_months else 0,
        "remote": 1 if not profile.remote_preference or job.remote_status == RemoteStatus.remote else 0.5 if job.remote_status in {RemoteStatus.hybrid, RemoteStatus.unknown} else 0,
        "compensation": 1 if not profile.paid_only or job.compensation_status == CompensationStatus.paid else 0.5 if job.compensation_status == CompensationStatus.unknown else 0,
    }
    job.match_breakdown = {k: round(v * MATCH_WEIGHTS[k]) for k, v in factors.items()}
    job.match_score = sum(job.match_breakdown.values())
    if job.eligibility_status == "Likely Not Eligible":
        penalty = max(0, job.match_score - 49)
        job.match_breakdown["eligibility constraint"] = -penalty
        job.match_score -= penalty
    job.match_reasons = [f"{k.title()}: {v:+d} points" for k, v in job.match_breakdown.items()]
    job.match_reasons += job.eligibility_reasons
    if not required:
        job.match_reasons.append("Required skills are not stated; skill fit is uncertain")
    if not profile.skills:
        job.match_reasons.append("Add your skills to personalize matching")
    opportunity = {"match": job.match_score, "eligibility": job.eligibility_score, "trust": job.company.trust_score, "freshness": job.freshness_score, "urgency": job.urgency_score}
    job.score_breakdown = {k: round(opportunity[k] * weight / 100) for k, weight in OPPORTUNITY_WEIGHTS.items()}
    job.opportunity_score = sum(job.score_breakdown.values())
    if job.hidden or not job.active or job.company.excluded:
        job.application_priority = "Hidden / Rejected"
    elif job.match_score >= 80 and job.eligibility_status == "Likely Eligible" and job.company.trust_score >= 65 and job.compensation_status == CompensationStatus.paid and profile.skills:
        job.application_priority = "Apply Now"
    elif job.match_score >= 70 and job.eligibility_status != "Likely Not Eligible" and not job.suspicious and profile.skills:
        job.application_priority = "Strong Match"
    elif job.match_score >= 45:
        job.application_priority = "Worth Exploring"
    else:
        job.application_priority = "Low Match"
    job.relevance_score, job.score_reasons = job.match_score, job.match_reasons
    return job
