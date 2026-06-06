import re
from app.models import CompensationStatus, Job, RemoteStatus
from app.profile import AVOID_SIGNALS, PREFERRED_SKILLS, PREFERRED_TITLES, STARTUP_SIGNALS

OCEAN_SKILLS = {"react", "next.js", "nextjs", "javascript", "typescript", "node.js", "node", "mongodb", "html", "css", "tailwind", "fastapi", "python"}


def extract_experience_years(text: str) -> int | None:
    # Match patterns like: "2+ years", "3 years", "5+ yrs", "2-3 years", "experience of 3 years"
    matches = re.findall(r'\b(\d+)\+?\s*(?:yr|year)s?\b', text)
    years = [int(m) for m in matches]
    # Also look for ranges e.g. 3-5 years
    ranges = re.findall(r'\b(\d+)\s*[-–]\s*(\d+)\s*(?:yr|year)s?\b', text)
    for r in ranges:
        years.append(int(r[0]))
        years.append(int(r[1]))
    if years:
        valid_years = [y for y in years if 0 < y < 20]
        return max(valid_years) if valid_years else None
    return None


def score_job(job: Job) -> Job:
    title = job.title.lower()
    description = job.description.lower()
    text = f"{title} {description} {' '.join(job.tags)}".lower()
    
    score = 20
    reasons = []
    
    # 1. React / Next.js Match (up to 25 points)
    react_bonus = 0
    if "react" in text:
        react_bonus += 15
    if "next.js" in text or "nextjs" in text:
        react_bonus += 10
    score += react_bonus
    if react_bonus > 0:
        reasons.append(f"React/Next.js alignment (+{react_bonus})")
        
    # 2. Frontend / Web Development Match (up to 25 points)
    frontend_bonus = 0
    if any(t in title for t in ["frontend", "front-end", "front end", "web"]):
        frontend_bonus += 15
    elif any(s in text for s in ["javascript", "typescript", "html", "css", "tailwind"]):
        frontend_bonus += 10
    score += frontend_bonus
    if frontend_bonus > 0:
        reasons.append(f"Frontend/Web focus (+{frontend_bonus})")
        
    # 3. Remote Preference (up to 15 points)
    if job.remote_status == RemoteStatus.remote:
        score += 15
        reasons.append("Remote workspace matched (+15)")
    elif job.remote_status == RemoteStatus.hybrid:
        score += 5
        reasons.append("Hybrid workspace matched (+5)")
        
    # 4. Paid stipend Preference (up to 15 points)
    if job.compensation_status == CompensationStatus.paid:
        score += 15
        reasons.append("Paid stipend (+15)")
    elif job.compensation_status == CompensationStatus.unpaid:
        score -= 20
        reasons.append("Unpaid list penalty (-20)")
    else:
        score -= 5
        reasons.append("Unclear compensation penalty (-5)")
        
    # 5. Startup Preference (up to 10 points)
    startup_matches = [term for term in STARTUP_SIGNALS if term in text]
    if startup_matches:
        score += 10
        reasons.append("Startup environment signal (+10)")
        
    # 6. Entry-level friendliness & AI Interest (up to 10 points)
    entry_bonus = 0
    if any(term in text for term in ["student", "freshman", "sophomore", "undergrad", "entry-level", "first-year", "1st year"]):
        entry_bonus += 5
    ai_keywords = ["ai", "llm", "openai", "rag", "agent", "gpt", "nlp", "machine learning", "ml"]
    if any(kw in title or re.search(r"\b" + kw + r"\b", text) for kw in ai_keywords):
        entry_bonus += 5
    score += entry_bonus
    if entry_bonus > 0:
        reasons.append(f"Entry-level/AI project match (+{entry_bonus})")
        
    # Years of experience penalty
    exp_years = extract_experience_years(description)
    if exp_years and exp_years >= 2:
        penalty = min(30, 15 * (exp_years - 1))
        score -= penalty
        reasons.append(f"Requires {exp_years}+ years experience (-{penalty})")
        
    # Seniority keywords in description penalty
    avoid_matches = [term for term in AVOID_SIGNALS if term in text]
    if avoid_matches:
        penalty = min(20, 10 * len(avoid_matches))
        score -= penalty
        reasons.append(f"Senior requirements risk penalty (-{penalty})")
        
    # Certificate/fake internship red flag penalty
    red_flags = ["certificate internship", "unified mentor", "internpe", "bharat intern", "wake up whistle"]
    if any(flag in text for flag in red_flags) or any(flag in job.company.name.lower() for flag in red_flags):
        score -= 50
        reasons.append("Flagged: training program or red-flag keyword (-50)")

    # Trust score alignment
    if job.company.trust_score < 40 and job.company.suspicious:
        score -= 10
        reasons.append("Low trust company penalty (-10)")
    elif job.company.trust_score >= 80:
        score += 5
        reasons.append("High trust company bonus (+5)")
        
    # Calculate matching and missing skills
    job_skills = {s.lower() for s in job.required_skills}
    if not job_skills:
        all_profile_skills = {"react", "next.js", "nextjs", "javascript", "typescript", "node.js", "node", "mongodb", "fastapi", "python", "html", "css", "tailwind"}
        found_skills = {s for s in all_profile_skills if re.search(r"\b" + re.escape(s) + r"\b", text)}
        job_skills = found_skills
        
    matching_skills = sorted(list(job_skills.intersection(OCEAN_SKILLS)))
    missing_skills = sorted(list(job_skills.difference(OCEAN_SKILLS)))
    
    # Store fields
    job.match_score = max(0, min(100, score))
    job.match_reasons = reasons
    job.matching_skills = matching_skills
    job.missing_skills = missing_skills
    
    # Priority buckets:
    if job.match_score >= 80 and job.compensation_status == CompensationStatus.paid and not job.suspicious:
        job.application_priority = "Apply Today"
    elif job.match_score >= 60 and not job.suspicious:
        job.application_priority = "Apply This Week"
    else:
        job.application_priority = "Low Priority"
        
    # Sync with relevance_score for backwards compatibility
    job.relevance_score = job.match_score
    job.score_reasons = reasons
    
    return job


