from app.models import CompensationStatus, Job, RemoteStatus
from app.profile import AVOID_SIGNALS, PREFERRED_SKILLS, PREFERRED_TITLES, STARTUP_SIGNALS


def score_job(job: Job) -> Job:
    text = f"{job.title} {job.description} {' '.join(job.tags)}".lower()
    score = 40
    reasons: list[str] = []

    title_matches = [term for term in PREFERRED_TITLES if term in text]
    if title_matches:
        score += min(25, 8 * len(title_matches))
        reasons.append(f"Title/profile match: {', '.join(sorted(title_matches)[:3])}")

    skill_matches = sorted(set(job.required_skills).intersection(PREFERRED_SKILLS))
    if skill_matches:
        score += min(20, 4 * len(skill_matches))
        reasons.append(f"Skill match: {', '.join(skill_matches[:5])}")

    if job.remote_status == RemoteStatus.remote:
        score += 12
        reasons.append("Remote friendly")
    elif job.remote_status == RemoteStatus.hybrid:
        score += 5
        reasons.append("Hybrid option")

    if job.location and "india" in job.location.lower():
        score += 10
        reasons.append("India location signal")

    if job.compensation_status == CompensationStatus.paid:
        score += 18
        reasons.append("Paid opportunity")
    elif job.compensation_status == CompensationStatus.unpaid:
        score -= 45
        reasons.append("Unpaid listing")
    else:
        score -= 8
        reasons.append("Compensation unclear")

    startup_matches = [term for term in STARTUP_SIGNALS if term in text]
    if startup_matches:
        score += 8
        reasons.append("Startup-friendly signal")

    avoid_matches = [term for term in AVOID_SIGNALS if term in text]
    if avoid_matches:
        score -= min(35, 12 * len(avoid_matches))
        reasons.append(f"Requirement risk: {', '.join(sorted(avoid_matches)[:3])}")

    job.relevance_score = max(0, min(100, score))
    job.score_reasons = reasons
    return job

