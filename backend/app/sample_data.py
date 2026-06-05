from app.models import Company, CompensationStatus, Job, RemoteStatus, SourceName


def sample_jobs() -> list[Job]:
    return [
        Job(
            id="sample-frontend",
            company=Company(
                id="sample-company-1",
                name="SeedStage Tools",
                website_url="https://example.com",
                linkedin_url="https://linkedin.com/company/example",
                description="A founder-led SaaS startup building API tooling for small engineering teams.",
                trust_score=85,
                suspicious=False,
                trust_reasons=["Company website present", "LinkedIn company page present", "Product or customer signal"],
            ),
            title="Frontend Developer Intern",
            url="https://example.com/jobs/frontend-intern",
            description="Paid remote React internship working on dashboards, APIs, and customer-facing UI.",
            required_skills=["react", "javascript", "api", "css"],
            location="Remote, India",
            remote_status=RemoteStatus.remote,
            compensation="Paid stipend",
            compensation_status=CompensationStatus.paid,
            source=SourceName.remoteok,
            relevance_score=94,
            score_reasons=["Title/profile match: frontend, react", "Remote friendly", "Paid opportunity"],
            tags=["internship", "remote", "startup"],
        ),
        Job(
            id="sample-suspicious",
            company=Company(
                id="sample-company-2",
                name="Growth Hustle Academy",
                description="Internship program",
                trust_score=30,
                suspicious=True,
                trust_reasons=["Missing company website", "LinkedIn company page missing", "Thin company description"],
            ),
            title="Software Engineer Intern",
            url="https://example.org/internship",
            description="Unpaid role with vague responsibilities and senior-level ownership.",
            required_skills=["javascript"],
            location="Remote",
            remote_status=RemoteStatus.remote,
            compensation="Unpaid",
            compensation_status=CompensationStatus.unpaid,
            source=SourceName.wellfound,
            relevance_score=22,
            score_reasons=["Unpaid listing", "Requirement risk: senior"],
            tags=["internship", "remote"],
            suspicious=True,
        ),
    ]

