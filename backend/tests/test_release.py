import asyncio
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.config import Settings
from app.main import app, get_repository, settings
from app.services.repository import make_repository


@pytest.fixture
def demo(monkeypatch):
    monkeypatch.setattr(settings, "public_demo_mode", True)
    repository = make_repository(Settings(_env_file=None, public_demo_mode=True))
    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.parametrize("path", ["/api/profile", "/api/searches", "/api/discovery/run", "/api/resume/analyze", "/api/applications/id", "/api/internships/id/corrections"])
def test_demo_blocks_mutations(demo, path):
    for method in ("post", "put", "patch", "delete"):
        response = demo.request(method.upper(), path, json={})
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "DEMO_READ_ONLY"


@pytest.mark.parametrize("path", ["/api/runtime", "/api/health", "/api/ready", "/api/internships", "/api/analytics/market", "/api/providers/health", "/api/export.csv", "/api/export.xlsx"])
def test_demo_read_paths(demo, path):
    assert demo.get(path).status_code == 200


def test_demo_private_state_is_not_exposed(demo):
    jobs = demo.get("/api/internships?include_inactive=true&limit=100").json()["items"]
    assert jobs and all(not j["notes"] and not j["contact"] and not j["corrections"] and not j["favorite"] and j["application_status"] == "not_applied" for j in jobs)
    assert demo.get("/api/applications").json() == []
    assert demo.get("/api/searches").json() == []
    assert demo.get("/api/profile").json()["name"] == "Demo candidate"
    assert demo.get("/api/runtime").json()["storage"] == "public_snapshot"


def test_production_cannot_silently_use_local_json():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", api_token="test-token")
    config = Settings(_env_file=None, app_env="production", api_token="test-token", public_demo_mode=True)
    repository = make_repository(config)
    with pytest.raises(PermissionError):
        asyncio.run(repository.put_state("profile", {"name":"intruder"}))


def test_demo_repository_reads_are_detached():
    repository = make_repository(Settings(_env_file=None, public_demo_mode=True))
    profile = asyncio.run(repository.profile())
    profile.name = "modified"
    assert asyncio.run(repository.profile()).name == "Demo candidate"
