from datetime import datetime, timedelta, timezone
import pytest
from app.models import RawInternship, CandidateProfile
from app.pipeline.normalizer import normalize_job, classify_skills, extract_skills
from app.pipeline.scorer import score_job
from app.pipeline.trust import risk_signals
from app.pipeline.dedupe import merge_jobs
from app.pipeline.geography import countries_in
from app.services.search import Filters, filter_jobs, interpret_query
from app.services.repository import LocalJsonRepository
from test_pipeline import make_job, student


@pytest.mark.parametrize('text,risky', [
 ('Pay \u20b92,000 registration fee before joining. Contact recruiter only on Telegram.', True),
 ('We never charge candidates any fee to apply.', False),
 ('There is no fee to apply.', False),
 ('Contact support on WhatsApp if needed.', False),
 ('WhatsApp-only recruitment.', True),
 ('Guaranteed earnings after registration.', True),
 ('No fee to apply, but pay a registration deposit before hiring.', True),
])
def test_risk_negation_and_contrast(text,risky):
    assert bool(risk_signals(text)) is risky
    job = score_job(make_job(description=text,url='https://boards.greenhouse.io/acme/jobs/1'),student())
    if risky:
        assert job.risk_state == 'quarantined'
        assert filter_jobs([job],Filters()) == []
        assert filter_jobs([job],Filters(include_risky=True)) == [job]
        assert not job.company.suspicious


def test_url_shortener_needs_review():
    job=score_job(make_job(url='https://bit.ly/something'),student())
    assert job.risk_state == 'review'
    assert job.application_priority not in {'Strong Match','Apply Now'}


@pytest.mark.parametrize('required', [[],['react','java','python','aws']])
def test_unknown_and_weak_requirements_do_not_recommend(required):
    job=score_job(make_job(required_skills=required),student())
    assert job.application_priority not in {'Strong Match','Apply Now'}
    assert job.match_score <= 64
    if not required:
        assert job.fit_score is None
        assert job.skill_evidence_confidence == 0


def test_skill_requirement_categories():
    required,preferred,mentioned=classify_skills('Requirements:\nReact and JavaScript\nNice to have:\nTypeScript\nResponsibilities:\nUse Docker.\nPython is not required.')
    assert required == ['javascript','react']
    assert preferred == ['typescript']
    assert {'docker','python'} <= set(mentioned)
    assert extract_skills('GitHub nodes') == []
    assert {'tailwind','accessibility','vitest','playwright','numpy','kubernetes'} <= set(extract_skills('Tailwind a11y Vitest Playwright NumPy K8s'))


def test_us_pronoun_not_geography():
    assert countries_in('Build products with us remotely.') == []
    assert countries_in('US-only remote internship') == ['United States']


def test_live_description_regressions():
    job=score_job(make_job(location='Hybrid - San Francisco',description='Millions of developers worldwide. About You:\nStrong knowledge and capability with JavaScript and TypeScript.\nCompensation & Benefits:\nSalary USD 1000/month.'),student())
    assert not job.worldwide_remote
    assert classify_skills(job.description)[0] == ['javascript','typescript']
    assert classify_skills('Minimum requirements\nProgramming fundamentals. We work mostly in Java and JavaScript.\nPreferred qualifications\nExperience with Python')[0] == []
    assert classify_skills('Minimum requirements\nProgramming fundamentals. We work mostly in Java and JavaScript.\nPreferred qualifications\nExperience with Python')[1] == ['python']


def test_company_remote_boilerplate_not_role_evidence():
    from app.pipeline.normalizer import normalize_remote_status
    assert normalize_remote_status('unknown','Seattle','We have remote employees across the globe.') == 'unknown'
    assert normalize_remote_status('unknown','India','This internship is fully remote.') == 'remote'


def test_foreign_location_needs_confirmation():
    job=score_job(make_job(location='London',remote_status='unknown',description='Bachelor degree in computer science. React required.'),student(education='B.Tech Computer Science'))
    assert job.eligibility_status == 'Unclear'


def test_ineligible_not_worth_exploring_label():
    job=score_job(make_job(location='Remote US-only'),student())
    assert job.application_priority == 'Low Match'


@pytest.mark.parametrize('query,expected',[
 ('remote internships in Canada',{'remote':'remote','country':'Canada'}),
 ('paid React internships',{'paid':True,'skill':'react'}),
 ('frontend internships in India',{'role':'frontend','country':'India'}),
 ('remote paid software internships for students',{'remote':'remote','paid':True,'role':'software engineering'}),
 ('AI internships in Bangalore',{'role':'AI/ML','country':'India'}),
])
def test_interpret_search(query,expected):
    parsed=interpret_query(query)
    for key,value in expected.items():
        assert parsed['filters'][key] == value


def test_residual_search_and_geography_not_discarded():
    job=score_job(make_job(location='Remote, India'),student())
    assert not filter_jobs([job],Filters(q='remote internships in Canada'))
    assert interpret_query('paid frontend internships underwater')['unparsed'] == 'underwater'
    assert not filter_jobs([job],Filters(q='paid frontend internships underwater'))


@pytest.mark.parametrize('query', ['paid remote hybrid internships','paid frontend backend internships','paid internships in Canada or India'])
def test_multiple_constraints_not_overwritten(query):
    parsed=interpret_query(query)
    assert parsed['unparsed'] and parsed['warnings']


def test_negated_query_not_pretended_supported():
    parsed=interpret_query('not remote internships')
    assert parsed['filters'] == {}
    assert parsed['unparsed'] == 'not remote internships'
    assert parsed['warnings']


def test_catalog_not_inventory():
    job=score_job(normalize_job(RawInternship(source='public_datasets',company_name='Program',title='Open source internship program',url='https://example.com/program')),student())
    assert not job.active
    assert not filter_jobs([job],Filters(include_inactive=True))
    assert filter_jobs([job],Filters(include_inactive=True,include_programs=True))


@pytest.mark.parametrize('change',[
 {'source':'github_jobs','title':'Backend Intern'},
 {'source':'github_jobs','location':'London'},
 {'source':'github_jobs','source_id':'different-team'},
])
def test_generic_careers_url_not_identity(change):
    a=make_job(url='https://example.com/careers',source_id='a',location='India')
    b=make_job(url=a.url,**change)
    assert len(merge_jobs([a],[b])[0]) == 2


def test_generic_url_not_sql_provider_id():
    job=normalize_job(RawInternship(source='github_jobs',source_id='https://example.com/careers',url='https://example.com/careers',title='Frontend Intern',company_name='Example'))
    assert job.source_id is None
    assert job.source_instances[0]['provider_job_id'] == ''


def test_ats_distinct_requisitions_not_fuzzy():
    text='A detailed internship with frontend engineering responsibilities. '*10
    a=make_job(url='https://boards.greenhouse.io/acme/jobs/1',description=text,location='India')
    b=make_job(url='https://boards.greenhouse.io/acme/jobs/2',source='github_jobs',description=text,location='India')
    assert len(merge_jobs([a],[b])[0]) == 2


def test_greenhouse_requisition_across_tracker_mirrors():
    a=make_job(url='https://boards.greenhouse.io/embed/job_app?token=8847738002')
    b=make_job(source='github_jobs',url='https://databricks.com/company/careers/open-positions/job?gh_jid=8847738002')
    assert len(merge_jobs([a],[b])[0]) == 1


def test_reset_source_values():
    job=normalize_job(RawInternship(source='yc_jobs',company_name='Example',title='Frontend Intern',url='https://example.com/jobs/1',description='Remote internship. React required.'))
    job.corrections={'remote_status':'onsite'}
    assert score_job(job,student()).remote_status == 'onsite'
    job.corrections={}
    assert score_job(job,student()).remote_status == 'remote'


@pytest.mark.asyncio
async def test_lease_owner_and_recovery(tmp_path):
    repo=LocalJsonRepository(tmp_path/'jobs.json')
    assert await repo.acquire_discovery('a',900)
    assert not await repo.acquire_discovery('b',900)
    await repo.release_discovery('b')
    assert not await repo.acquire_discovery('b',900)
    await repo.release_discovery('a')
    assert await repo.acquire_discovery('b',900)
    run=await repo.create_discovery_run('internship',10)
    state=await repo.get_state('run:'+run)
    state['started_at']=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()
    await repo.put_state('run:'+run,state)
    await repo.recover_runs(900)
    assert (await repo.list_runs())[0]['status'] == 'cancelled'
