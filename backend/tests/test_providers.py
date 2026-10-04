import json
from html import escape

import httpx
import pytest

from app.config import Settings
from app.providers.base import PoliteClient
from app.providers.remoteok import RemoteOKProvider
from app.providers.startup_career_pages import StartupCareerPagesProvider
from app.providers.simplify_jobs import SimplifyJobsProvider
from app.providers.yc_jobs import YCJobsProvider
from app.providers.registry import get_providers


def mock_client(provider, handler):
    provider.client = lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_remoteok_logo_not_website():
    provider = RemoteOKProvider(Settings(_env_file=None))
    mock_client(provider,lambda request:httpx.Response(200,json=[{"legal":"terms"},{"id":1,"position":"React Internship","company":"Example","url":"https://example.com/job","company_logo":"https://cdn.example.com/logo.png","description":"React internship"}]))
    jobs = await provider.discover("internship",10)
    assert len(jobs) == 1 and jobs[0].company_website is None
    assert jobs[0].compensation is None and jobs[0].date_posted is None


@pytest.mark.asyncio
async def test_greenhouse_boundaries_content_and_unknown_pay():
    provider = StartupCareerPagesProvider(Settings(_env_file=None,greenhouse_boards=["example"]))
    def handler(request):
        assert request.url.params["content"] == "true"
        return httpx.Response(200,json={"jobs":[{"title":"Internal Systems Engineer","absolute_url":"https://example.com/internal"},{"title":"Frontend Intern","absolute_url":"https://example.com/intern?gh_jid=123","content":"React UI development","location":{"name":"India"},"updated_at":"2026-09-01T00:00:00Z"}]})
    mock_client(provider,handler)
    jobs = await provider.discover("internship",1)
    assert len(jobs) == 1 and jobs[0].title == "Frontend Intern"
    assert jobs[0].description == "React UI development"
    assert jobs[0].compensation is None and jobs[0].date_posted is None
    assert "gh_jid=123" in jobs[0].url


@pytest.mark.asyncio
async def test_simplify_closed_and_missing_evidence():
    provider = SimplifyJobsProvider(Settings(_env_file=None))
    html = '<table><tbody><tr><td>Example</td><td>Frontend Intern</td><td>India</td><td><a href="https://example.com/job">Apply</a></td><td>unknown</td></tr><tr><td>Other</td><td>Intern</td><td>US</td><td>closed</td><td>1d</td></tr></tbody></table>'
    mock_client(provider,lambda request:httpx.Response(200,text=html))
    jobs = await provider.discover("internship",20)
    assert len(jobs) == 1
    assert jobs[0].compensation is None and jobs[0].date_posted is None


@pytest.mark.asyncio
async def test_yc_structured_data_and_deadline():
    provider = YCJobsProvider(Settings(_env_file=None))
    listing={"props":{"jobPostings":[{"id":123,"title":"React Intern","type":"Internship","companyName":"Example","url":"/companies/example/jobs/123","location":"India"}]}}
    detail={"@type":"JobPosting","description":"React internship","datePosted":"2026-09-01","validThrough":"2026-10-01","hiringOrganization":{"sameAs":"https://example.com"}}
    mock_client(provider,lambda request:httpx.Response(200,text='<div data-page="'+escape(json.dumps(listing),quote=True)+'"></div>' if request.url.path=="/jobs" else '<script type="application/ld+json">'+json.dumps(detail)+'</script>'))
    jobs = await provider.discover("internship",20)
    assert jobs[0].company_name == "Example"
    assert jobs[0].deadline.year == 2026 and jobs[0].deadline.month == 10
    assert jobs[0].description == "React internship"


@pytest.mark.asyncio
async def test_provider_cache_and_bounded_retry(monkeypatch):
    calls=[]
    async def get(self,url,**kwargs):
        calls.append(url)
        return httpx.Response(429 if len(calls)==1 else 200,request=httpx.Request("GET",url),headers={"Retry-After":"0"})
    async def no_sleep(_):
        pass
    monkeypatch.setattr(httpx.AsyncClient,"get",get)
    monkeypatch.setattr("app.providers.base.asyncio.sleep",no_sleep)
    PoliteClient.cache.clear()
    async with PoliteClient(Settings(_env_file=None,provider_request_interval=0),[]) as client:
        assert (await client.get("https://cache.example/test")).status_code == 200
        await client.get("https://cache.example/test")
    assert len(calls)==2


def test_restricted_sources_disabled_by_default():
    names={p.source.value for p in get_providers(Settings(_env_file=None))}
    assert "wellfound" not in names and "work_at_a_startup" not in names
    assert get_providers(Settings(_env_file=None),[]) == []
