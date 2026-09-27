from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
import json

import httpx
import pytest

from app.config import Settings
from app.models import CandidateProfile, Company, DiscoveryRequest, Job, RawInternship, SourceName
from app.pipeline.dedupe import canonical_company, canonical_title, canonical_url, merge_jobs
from app.pipeline.filters import is_phase_one_candidate, rejection_reason
from app.pipeline.normalizer import normalize_job, normalize_compensation, parse_salary, experience_months
from app.pipeline.runner import run_discovery
from app.pipeline.scorer import score_job
from app.services.ai import Classification, classify
from app.services.repository import LocalJsonRepository
from app.services.search import Filters, filter_jobs, sort_jobs


def make_job(**changes):
    values = dict(company=Company(name="Example", website_url="https://example.com"),
                  title="Frontend Intern", url="https://example.com/jobs/1", source=SourceName.yc_jobs,
                  description="Paid internship. Requires 0 months experience. Graduating 2028-2030. React JavaScript. Remote.",
                  required_skills=["react", "javascript"], remote_status="remote", compensation_status="paid",
                  date_posted=datetime.now(timezone.utc))
    values.update(changes)
    return Job(**values)


def student(**changes):
    return CandidateProfile(**({"skills": ["React", "JavaScript"], "graduation_year": 2029, "country": "India", "experience_months": 3} | changes))


@pytest.mark.parametrize("title,expected", [
    ("SWE Intern", True), ("Frontend Internship", True), ("Web Developer Co-op", True),
    ("Undergrad Student Fellow", True), ("Internal Systems Developer", False),
    ("Senior Developer Intern", False), ("Product Manager Intern", True),
    ("Product Manager, International", False), ("Staff Engineer", False),
])
def test_internship_boundaries(title, expected):
    assert is_phase_one_candidate(make_job(title=title, description="")) is expected


def test_aliases_and_identity():
    assert canonical_title("SWE Intern") == canonical_title("Software Engineering Internship")
    assert canonical_company("Example Inc.") == "example"
    assert canonical_company("Example Labs") != canonical_company("Example")
    assert canonical_url("https://EXAMPLE.com/Jobs/ABC?job=1&utm_source=tracker") == "https://example.com/Jobs/ABC?job=1"
    assert canonical_url("https://example.com/?job=1") != canonical_url("https://example.com/?job=2")


@pytest.mark.parametrize("pay,expected", [
    ("Paid internship", "paid"), ("Unpaid internship", "unpaid"), ("Salary TBD", "unknown"),
    ("Paid media marketing", "unknown"), (None, "unknown"), ("INR 15,000/month", "paid"),
])
def test_compensation_evidence(pay, expected):
    assert normalize_compensation(pay, "") == expected


def test_salary_units():
    assert parse_salary("INR 15,000-25,000/month") == dict(stipend_min=15000, stipend_max=25000, compensation_currency="INR", compensation_period="month")
    assert parse_salary("$20-30/hour")["stipend_max"] == 30
    assert parse_salary("USD 50k/year")["stipend_min"] == 50000
    assert parse_salary("Competitive stipend") == {}


def test_experience_not_company_age():
    assert experience_months("Our 10 years of innovation. 3 months of work experience required.") == 3
    assert experience_months("Founded 5 years ago") is None


def test_normalization_does_not_invent_facts():
    job = normalize_job(RawInternship(source="yc_jobs",title="Frontend Intern",company_name="Example Inc.",url="https://example.com/jobs/1?ref=abc",description="<p>React and HTML internship.</p>",location="  Bengaluru  "))
    assert job.country == "India"
    assert job.compensation_status == "unknown"
    assert job.date_posted is None
    assert job.remote_status == "unknown"
    assert "<p>" not in job.description
    assert job.original_urls == ["https://example.com/jobs/1?ref=abc"]


def test_high_fit_and_explanation_math():
    job = score_job(make_job(), student())
    assert job.match_score == 100
    assert job.match_score == sum(job.match_breakdown.values())
    assert job.opportunity_score == sum(job.score_breakdown.values())
    assert job.eligibility_status == "Likely Eligible"
    assert job.application_priority == "Strong Match"  # Domain evidence is not independent verification.


def test_profile_controls_match():
    a = score_job(make_job(), student())
    b = score_job(make_job(), student(skills=["java"],preferred_roles=["backend"]))
    assert a.match_score > b.match_score + 40
    assert b.missing_skills == ["javascript", "react"]
    empty = score_job(make_job(), CandidateProfile())
    assert empty.application_priority != "Apply Now"


@pytest.mark.parametrize("description,reason", [
    ("Requires 2 years of experience.", "experience"),
    ("Graduating 2026-2027.", "Graduation"),
    ("Remote US-only internship.", "US"),
])
def test_explicit_eligibility_conflicts(description, reason):
    job = score_job(make_job(description=description), student())
    assert job.eligibility_status == "Likely Not Eligible"
    assert job.match_score <= 49
    assert any(reason in r for r in job.eligibility_reasons)


def test_uncertain_eligibility():
    job = score_job(make_job(description="A React internship"), student())
    assert job.eligibility_status == "Unclear"


def test_preferences_lower_rank_not_delete():
    good = score_job(make_job(), student())
    other = score_job(make_job(remote_status="onsite",compensation_status="unpaid"), student())
    assert good.match_score - other.match_score == 20
    assert rejection_reason(other) is None


def test_trust_policy_and_scam_signals():
    blocked = score_job(make_job(company=Company(name="Unified Mentor")), student())
    assert blocked.company.trust_score == 0
    assert blocked.application_priority == "Hidden / Rejected"
    assert rejection_reason(blocked) == "REJECTED_EXCLUDED_COMPANY"
    scam = score_job(make_job(description="Pay a registration fee to apply. Telegram only. Guaranteed income."), student())
    assert scam.suspicious
    ats = score_job(make_job(url="https://boards.greenhouse.io/example/jobs/123"), student())
    assert ats.company.trust_score >= 65
    assert any("ATS" in reason for reason in ats.company.trust_reasons)


@pytest.mark.parametrize("url",["javascript:alert(1)","http://127.0.0.1/job","http://169.254.169.254/latest","https://user:pass@example.com/job","file:///tmp/job"])
def test_invalid_application_links(url):
    assert rejection_reason(make_job(url=url)) == "REJECTED_INVALID_URL"


def test_dedupe_preserves_requisitions_and_user_fields():
    old = make_job(id="existing", notes="Keep this",favorite=True,application_status="interview")
    duplicate = make_job(url=old.url+"?utm_source=other",source="github_jobs",description=old.description*3)
    merged, counts = merge_jobs([old],[duplicate, duplicate])
    assert len(merged) == 1
    assert merged[0].id == "existing"
    assert merged[0].notes == "Keep this"
    assert merged[0].favorite
    assert merged[0].application_status == "interview"
    assert merged[0].source_count == 2
    assert merged[0].source == old.source
    assert merged[0].url == old.url
    assert len(merged[0].sources) == 2
    different = make_job(url="https://example.com/jobs/2",source_id="2")
    same_title = make_job(url="https://example.com/jobs/3",source_id="3")
    assert len(merge_jobs([different],[same_title])[0]) == 2
    assert counts["duplicates"] == 2


def test_cross_source_fuzzy_requires_corroboration():
    a = make_job(description="Build frontend React user interfaces with the product team. "*5, location="India")
    b = make_job(title="Frontend Internship",source="github_jobs",url="https://tracker.example/job",description=a.description,location="India")
    assert len(merge_jobs([a],[b])[0]) == 1
    b.location = "London"
    assert len(merge_jobs([a],[b])[0]) == 2


def test_lifecycle_retains_old_jobs():
    job = make_job(last_seen=datetime.now(timezone.utc)-timedelta(days=100),date_posted=datetime.now(timezone.utc)-timedelta(days=100))
    assert not score_job(job,student()).active
    assert len(filter_jobs([job],Filters(include_inactive=True))) == 1
    assert filter_jobs([job],Filters()) == []


def test_search_combinations_and_currency_safety():
    job = score_job(make_job(compensation="USD 30/hour"), student())
    assert filter_jobs([job],Filters(q="show paid remote frontend internships with React and JavaScript")) == [job]
    assert filter_jobs([job],Filters(skill="react, javascript",paid=True,min_match=80)) == [job]
    assert filter_jobs([job],Filters(min_stipend=20,currency="USD",period="hour")) == [job]
    assert not filter_jobs([job],Filters(min_stipend=20,currency="INR",period="month"))
    assert not filter_jobs([job],Filters(source="remoteok"))
    assert sort_jobs([job,score_job(make_job(required_skills=["java"]),student())],"match")[0] == job


@pytest.mark.asyncio
async def test_repository_atomic_tracking_and_no_seed(tmp_path):
    repo = LocalJsonRepository(tmp_path/"jobs.json")
    assert await repo.list_jobs() == []
    await repo.upsert_jobs([make_job()])
    job = (await repo.list_jobs())[0]
    await repo.patch_job(job.id,{"notes":"Keep", "application_status":"applied","corrections":{"remote_status":"onsite"}})
    await repo.upsert_jobs([make_job()])
    new = (await repo.list_jobs())[0]
    assert new.notes == "Keep"
    assert score_job(new,student()).remote_status == "onsite"
    before = repo.path.read_bytes()
    await repo.list_jobs()
    assert repo.path.read_bytes() == before


@pytest.mark.asyncio
async def test_legacy_samples_and_fabricated_pay_not_recommended(tmp_path):
    repo = LocalJsonRepository(tmp_path/"jobs.json")
    repo._write([make_job(id="sample-frontend").model_dump(mode="json"), make_job(id="old",source="github_jobs",compensation="Paid stipend",description="Internship role at Example").model_dump(mode="json")])
    before = repo.path.read_bytes()
    jobs = await repo.list_jobs()
    assert jobs[0].hidden and jobs[0].provenance["sample"]
    assert jobs[1].compensation is None and jobs[1].compensation_status == "unknown"
    assert repo.path.read_bytes() == before


@pytest.mark.asyncio
async def test_discovery_persistence_isolation_and_reports(tmp_path, monkeypatch):
    repo = LocalJsonRepository(tmp_path/"jobs.json")
    good = type("Provider",(),{"source":SourceName.yc_jobs,"warnings":[],"discover":AsyncMock(return_value=[
        RawInternship(source="yc_jobs",source_id="1",title="Frontend Intern",company_name="Example",url="https://example.com/job",description="Paid internship with React."),
        RawInternship(source="yc_jobs",source_id="2",title="Senior Engineer",company_name="Example",url="https://example.com/senior"),
    ])})()
    bad = type("Provider",(),{"source":SourceName.remoteok,"warnings":[],"discover":AsyncMock(side_effect=httpx.ReadTimeout("timeout"))})()
    monkeypatch.setattr("app.pipeline.runner.get_providers",lambda *_:[good,bad])
    result = await run_discovery(Settings(_env_file=None),repo,DiscoveryRequest(persist=False))
    assert result.discovered == 1 and result.stored == 0
    assert result.metrics["rejected"] == 1
    assert result.metrics["provider_failures"] == 1
    assert await repo.list_runs() == []
    assert await repo.list_jobs() == []
    result = await run_discovery(Settings(_env_file=None),repo,DiscoveryRequest())
    assert result.stored == 1
    assert len(await repo.list_runs()) == 1
    result = await run_discovery(Settings(_env_file=None),repo,DiscoveryRequest())
    assert result.stored == 0 and result.metrics["duplicates"] == 1
    assert len(result.jobs) == 1


@pytest.mark.asyncio
async def test_ai_validation_fallback_and_cache(tmp_path):
    repo = LocalJsonRepository(tmp_path/"jobs.json")
    settings = Settings(_env_file=None,enable_ai_classification=True,ai_model="test")
    job = make_job(description="React required. TypeScript preferred.")
    provider = type("AI",(),{"classify_job":AsyncMock(return_value=Classification(confidence=.95,evidence="React required.",required_skills=["React","Rust"],preferred_skills=["TypeScript"]))})()
    assert await classify(job,settings,repo,provider) == "analyzed"
    assert "rust" not in job.required_skills
    assert "typescript" in job.preferred_skills
    assert await classify(job,settings,repo,provider) == "cached"
    assert provider.classify_job.await_count == 1
    provider.classify_job = AsyncMock(side_effect=ValueError("invalid model output"))
    assert await classify(make_job(description="Different job"),settings,repo,provider) == "fallback"
    provider.classify_job = AsyncMock(side_effect=httpx.ConnectError("unavailable"))
    assert await classify(make_job(description="Another job"),settings,repo,provider) == "fallback"
    with pytest.raises(ValueError):
        Classification.model_validate({"confidence":2,"match_score":100})

