import pytest
from pathlib import Path
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


def test_experience_penalty_lowers_score():
    job = Job(
        company=Company(name="Standard Corp", website_url="https://example.com"),
        title="React Frontend Developer Intern",
        url="https://example.com/jobs/2",
        description="Looking for an intern. Must have 5+ years of experience with React.",
        required_skills=["react"],
        remote_status=RemoteStatus.remote,
        compensation_status=CompensationStatus.paid,
        source=SourceName.remoteok,
    )
    scored = score_job(job)
    assert scored.relevance_score < 70
    assert any("experience" in reason.lower() for reason in scored.score_reasons)


def test_red_flag_unpaid_unified_mentor_penalized():
    job = Job(
        company=Company(name="Unified Mentor", website_url="https://example.com"),
        title="Frontend Intern",
        url="https://example.com/jobs/3",
        description="Unpaid training program and internship opportunity.",
        required_skills=["react"],
        remote_status=RemoteStatus.remote,
        compensation_status=CompensationStatus.unpaid,
        source=SourceName.remoteok,
    )
    scored = apply_trust(score_job(job))
    # Red flags should hit trust score and relevance score hard
    assert scored.relevance_score <= 10
    assert scored.company.trust_score == 0
    assert scored.suspicious is True


@pytest.mark.asyncio
async def test_run_discovery_records_audit():
    import pytest
    from unittest.mock import AsyncMock, MagicMock
    from app.pipeline.runner import run_discovery
    from app.models import DiscoveryRequest, RawInternship
    
    settings = MagicMock()
    settings.request_timeout_seconds = 2.0
    settings.discovery_user_agent = "TestBot"
    
    repository = MagicMock()
    repository.create_discovery_run = AsyncMock(return_value="test-run-id")
    repository.store_raw_jobs = AsyncMock()
    repository.upsert_jobs = AsyncMock(return_value=[])
    repository.update_discovery_run = AsyncMock()
    
    provider = MagicMock()
    provider.source = SourceName.remoteok
    provider.discover = AsyncMock(return_value=[
        RawInternship(
            source=SourceName.remoteok,
            source_id="123",
            title="React Intern",
            company_name="Good Company",
            url="https://example.com/job",
            description="Paid internship for React developers.",
            remote_status=RemoteStatus.remote,
        )
    ])
    
    import app.pipeline.runner
    orig_get_providers = app.pipeline.runner.get_providers
    app.pipeline.runner.get_providers = MagicMock(return_value=[provider])
    
    request = DiscoveryRequest(sources=[SourceName.remoteok], persist=True)
    try:
        response = await run_discovery(settings, repository, request)
        
        repository.create_discovery_run.assert_called_once_with(request.query, request.limit_per_source)
        repository.store_raw_jobs.assert_called_once()
        repository.update_discovery_run.assert_called_once()
        
        assert response.discovered == 1
    finally:
        app.pipeline.runner.get_providers = orig_get_providers


def test_repository_path_resolves_canonical():
    import os
    from app.config import get_settings
    from app.services.repository import make_repository
    
    settings = get_settings()
    if settings.supabase_enabled:
        return
        
    repo_default = make_repository(settings)
    path_default = repo_default.path.resolve()
    
    original_cwd = os.getcwd()
    try:
        # Move up to workspace root (one level up from backend)
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(root_dir)
        
        settings_root = get_settings()
        repo_root = make_repository(settings_root)
        path_root = repo_root.path.resolve()
        
        assert path_default == path_root
    finally:
        os.chdir(original_cwd)


def test_internship_filtering_word_boundary():
    from app.pipeline.filters import is_phase_one_candidate
    
    # Matching cases
    j_ok1 = Job(company=Company(name="A"), title="Software Engineer Intern", url="https://example.com/1", source=SourceName.yc_jobs)
    j_ok2 = Job(company=Company(name="B"), title="React Web Developer Co-op", url="https://example.com/2", source=SourceName.yc_jobs)
    j_ok3 = Job(company=Company(name="C"), title="Undergrad Student Fellow", url="https://example.com/3", source=SourceName.yc_jobs)
    
    assert is_phase_one_candidate(j_ok1) is True
    assert is_phase_one_candidate(j_ok2) is True
    assert is_phase_one_candidate(j_ok3) is True

    # Exclusions and False Positives (Internal / International / Senior)
    j_bad1 = Job(company=Company(name="D"), title="Software Engineer, Internal Systems", url="https://example.com/4", source=SourceName.yc_jobs)
    j_bad2 = Job(company=Company(name="E"), title="International Regulatory Exam Lead", url="https://example.com/5", source=SourceName.yc_jobs)
    j_bad3 = Job(company=Company(name="F"), title="Senior Developer Intern", url="https://example.com/6", source=SourceName.yc_jobs)
    j_bad4 = Job(company=Company(name="G"), title="Product Manager, Figma for Education (International)", url="https://example.com/7", source=SourceName.yc_jobs)

    assert is_phase_one_candidate(j_bad1) is False
    assert is_phase_one_candidate(j_bad2) is False
    assert is_phase_one_candidate(j_bad3) is False
    assert is_phase_one_candidate(j_bad4) is False


def test_ranking_engine_scoring():
    from app.pipeline.scorer import score_job
    
    # High match React, Paid, Remote startup
    j_high = Job(
        company=Company(name="Super Startup", trust_score=85),
        title="React Frontend Developer Intern",
        url="https://example.com/yc-stipend",
        description="We are building an early-stage YC startup. Looking for paid frontend intern with React/Next.js experience. Remote position.",
        required_skills=["react", "next.js", "javascript"],
        remote_status=RemoteStatus.remote,
        compensation="Paid stipend",
        compensation_status=CompensationStatus.paid,
        source=SourceName.yc_jobs
    )
    scored_high = score_job(j_high)
    assert scored_high.match_score >= 80
    assert scored_high.application_priority == "Apply Today"
    assert any("React/Next.js alignment" in reason for reason in scored_high.match_reasons)
    assert any("Frontend/Web focus" in reason for reason in scored_high.match_reasons)

    # Low match, unpaid/senior
    j_low = Job(
        company=Company(name="Big Corp", trust_score=50),
        title="Java backend developer",
        url="https://example.com/unpaid-java",
        description="Unpaid internship, must have 3+ years experience with Java Spring boot.",
        required_skills=["java"],
        remote_status=RemoteStatus.onsite,
        compensation_status=CompensationStatus.unpaid,
        source=SourceName.remoteok
    )
    scored_low = score_job(j_low)
    assert scored_low.match_score < 40
    assert scored_low.application_priority == "Low Priority"


@pytest.mark.asyncio
async def test_advanced_deduplication():
    from app.config import Settings
    from app.services.repository import LocalJsonRepository
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_dedupe.json"
        # Create repo
        repo = LocalJsonRepository(db_file)
        repo._write([]) # Clear out sample jobs for a clean test environment
        
        j1 = Job(
            company=Company(name="Palantir Technologies", website_url="https://palantir.com", trust_score=80),
            title="Year at Palantir - Forward Deployed Software Engineer",
            url="https://palantir.com/jobs/1",
            description="Software Engineering intern role",
            remote_status=RemoteStatus.hybrid,
            compensation="Paid stipend",
            compensation_status=CompensationStatus.paid,
            source=SourceName.simplify_jobs
        )
        j2 = Job(
            company=Company(name="Palantir", website_url="https://palantir.com", trust_score=75),
            title="Year at Palantir - Forward Deployed Software Engineer",
            url="https://palantir.com/jobs/2",
            description="Detailed software engineer intern description",
            remote_status=RemoteStatus.hybrid,
            compensation="Paid $5000/month",
            compensation_status=CompensationStatus.paid,
            source=SourceName.github_jobs
        )
        
        # Upsert first job
        await repo.upsert_jobs([j1])
        db_jobs = await repo.list_jobs()
        assert len(db_jobs) == 1
        assert db_jobs[0].source_count == 1
        assert db_jobs[0].sources == [SourceName.simplify_jobs]
        
        # Upsert second job (Primary duplicate matching company+title)
        await repo.upsert_jobs([j2])
        db_jobs = await repo.list_jobs()
        assert len(db_jobs) == 1  # Should merge!
        merged = db_jobs[0]
        assert merged.source_count == 2
        assert set(merged.sources) == {SourceName.simplify_jobs, SourceName.github_jobs}
        assert merged.company.trust_score == 80  # Max trust_score
        assert merged.compensation == "Paid $5000/month"  # Richest compensation
        assert len(merged.description) > len(j1.description)  # Richest description

        # Secondary match (same domain + similar title)
        j3 = Job(
            company=Company(name="Palantir Co", website_url="https://palantir.com"),
            title="Forward Deployed Software Developer", # Similar title keywords
            url="https://palantir.com/jobs/3",
            remote_status=RemoteStatus.hybrid,
            source=SourceName.yc_jobs
        )
        await repo.upsert_jobs([j3])
        db_jobs = await repo.list_jobs()
        assert len(db_jobs) == 1  # Secondary matching company and domain, similar keywords should merge!
        assert db_jobs[0].source_count == 3




