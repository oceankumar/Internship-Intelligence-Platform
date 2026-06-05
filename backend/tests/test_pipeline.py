from app.models import Company, CompensationStatus, Job, RemoteStatus, SourceName
from app.pipeline.scorer import score_job
from app.pipeline.trust import apply_trust


def test_profile_aligned_paid_remote_role_scores_high():
    job = Job(
        company=Company(
            name="Good Startup",
            website_url="https://example.com",
            linkedin_url="https://linkedin.com/company/good-startup",
            description="A product startup building developer tools for customers and small teams.",
        ),
        title="React Frontend Developer Intern",
        url="https://example.com/jobs/1",
        description="Paid remote internship building React UI and APIs with a founder-led engineering team.",
        required_skills=["react", "javascript", "api"],
        remote_status=RemoteStatus.remote,
        compensation="Paid stipend",
        compensation_status=CompensationStatus.paid,
        source=SourceName.remoteok,
    )

    scored = apply_trust(score_job(job))

    assert scored.relevance_score >= 80
    assert scored.company.trust_score >= 50
    assert scored.suspicious is False

