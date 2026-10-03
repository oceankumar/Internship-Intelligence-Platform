from app.models import CandidateProfile, CompensationStatus, Job, RemoteStatus
from app.pipeline.eligibility import evaluate_eligibility
from app.pipeline.lifecycle import refresh_lifecycle
from app.pipeline.normalizer import enrich_fields, extract_skills, experience_months
from app.pipeline.trust import apply_trust
from app.pipeline.geography import canonical_country

MATCH_WEIGHTS = {"skills": 40, "role": 25, "experience": 15, "remote": 10, "compensation": 10}
OPPORTUNITY_WEIGHTS = {"match": 45, "eligibility": 20, "trust": 15, "freshness": 15, "urgency": 5}


def extract_experience_years(text: str) -> int | None:
    months = experience_months(text)
    return months // 12 if months is not None else None


def score_job(job: Job, profile: CandidateProfile | None = None) -> Job:
    profile = profile or CandidateProfile()
    enrich_fields(job)
    for key, value in job.provenance.get("source_values", {}).items():
        if key in {"remote_status", "compensation_status", "required_skills"}:
            setattr(job, key, RemoteStatus(value) if key == "remote_status" else CompensationStatus(value) if key == "compensation_status" else value)
    proposal = job.provenance.get("ai_classification", {}).get("result", {})
    if proposal.get("evidence") and proposal["evidence"] in job.description:
        preferred = [s.lower() for s in proposal.get("preferred_skills", []) if s.lower() in job.description.lower()]
        required = [s.lower() for s in proposal.get("required_skills", []) if s.lower() in job.description.lower()]
        job.required_skills = sorted(set(job.required_skills + required) - set(preferred))
        job.preferred_skills = sorted(set(job.preferred_skills + preferred))
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
    preferred = set(s.casefold() for s in job.preferred_skills)
    job.matching_skills = sorted(required & skills)
    job.missing_skills = sorted(required - skills)
    factors = {
        "skills": len(required & skills) / len(required) if required else 0,
        "role": 1 if job.role_family in profile.preferred_roles else 0.3,
        "experience": 0 if job.minimum_experience_months is None else 1 if job.minimum_experience_months <= profile.experience_months else 0,
        "remote": 1 if not profile.remote_preference or job.remote_status == RemoteStatus.remote else 0,
        "compensation": 1 if not profile.paid_only or job.compensation_status == CompensationStatus.paid else 0,
    }
    if required and preferred:
        factors["skills"] = .95 * factors["skills"] + .05 * len(preferred & skills) / len(preferred)
    job.match_breakdown = {k: round(v * MATCH_WEIGHTS[k]) for k, v in factors.items()}
    job.match_score = sum(job.match_breakdown.values())
    job.fit_score = round((job.match_breakdown["skills"] + job.match_breakdown["role"] + job.match_breakdown["experience"]) * 100 / 80) if required else None
    job.skill_evidence_confidence = 100 if required else 40 if preferred else 0
    job.evidence_confidence = min(100, (40 if required else 0) + (20 if len(job.description.split()) >= 40 else 5) + (10 if job.minimum_experience_months is not None else 0) + (10 if job.graduation_years or job.degree_requirement else 0) + (10 if job.worldwide_remote or job.remote_countries or job.country else 0) + (10 if job.compensation_status != "unknown" else 0))
    country_preferences = {canonical_country(v) for v in profile.preferred_locations if v.strip()}
    geography = "matches" if job.worldwide_remote or not country_preferences else "unknown" if not job.country and not job.remote_countries else "matches" if country_preferences.intersection(job.remote_countries + ([job.country] if job.country else [])) else "conflicts"
    job.preference_compliance = {
        "paid": "matches" if not profile.paid_only or job.compensation_status == "paid" else "unknown" if job.compensation_status == "unknown" else "conflicts",
        "remote": "matches" if not profile.remote_preference or job.remote_status == "remote" else "unknown" if job.remote_status == "unknown" else "conflicts",
        "geography": geography,
        "role": "matches" if job.role_family in profile.preferred_roles else "conflicts",
    }
    job.uncertainties = []
    if not required:
        job.uncertainties.append("Required skills are unspecified; fit is unknown")
    if job.compensation_status == "unknown":
        job.uncertainties.append("Compensation is not confirmed")
    if job.remote_status == "remote" and not job.worldwide_remote and not job.remote_countries:
        job.uncertainties.append("Remote geography is not stated")
    if job.minimum_experience_months is None:
        job.uncertainties.append("Experience requirement is not stated")
    cap = 59 if not required else 64 if factors["skills"] < .75 else 100
    if geography == "conflicts":
        cap = min(cap, 64)
    if job.match_score > cap:
        job.match_breakdown["evidence/fit constraint"] = cap - job.match_score
        job.match_score = cap
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
    job.match_reasons += job.uncertainties + [f"{key.title()} preference: {value}" for key, value in job.preference_compliance.items()]
    opportunity = {"match": job.match_score, "eligibility": job.eligibility_score, "trust": job.trust_score, "freshness": job.freshness_score, "urgency": job.urgency_score}
    job.score_breakdown = {k: round(opportunity[k] * weight / 100) for k, weight in OPPORTUNITY_WEIGHTS.items()}
    job.opportunity_score = sum(job.score_breakdown.values())
    recommendable = job.risk_state == "normal" and all(v == "matches" for v in job.preference_compliance.values()) and required and factors["skills"] >= .75 and job.evidence_confidence >= 65 and profile.skills
    if job.hidden or not job.active or job.company.excluded or job.risk_state in {"quarantined", "blocked"}:
        job.application_priority = "Hidden / Rejected"
    elif recommendable and job.match_score >= 85 and job.eligibility_status == "Likely Eligible" and job.trust_score >= 65 and job.evidence_confidence >= 80:
        job.application_priority = "Apply Now"
    elif recommendable and job.match_score >= 75 and job.eligibility_status != "Likely Not Eligible" and not job.suspicious:
        job.application_priority = "Strong Match"
    elif job.match_score >= 45 and job.eligibility_status != "Likely Not Eligible":
        job.application_priority = "Worth Exploring"
    else:
        job.application_priority = "Low Match"
    job.relevance_score, job.score_reasons = job.match_score, job.match_reasons
    return job
