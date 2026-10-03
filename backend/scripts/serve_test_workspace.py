"""Isolated browser-test workspace; fixtures never enter the real data store."""
import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from app.main import app, get_repository
from app.models import CandidateProfile, RawInternship, SourceName
from app.services.repository import LocalJsonRepository


async def seed(repo):
    await repo.put_state("profile",CandidateProfile(name="Test Candidate",skills=["react","javascript","html","css"],country="India",graduation_year=2029,experience_months=3).model_dump())
    return


class FixtureProvider:
    source=SourceName.yc_jobs
    warnings=[]
    async def discover(self, query, limit):
        jobs=[]
        for i in range(16):
            jobs.append(RawInternship(source=self.source,source_id=str(i),company_name=["Test Acme","Test Studio","Test Research"][i%3],title=["Frontend Engineering Intern","Product Design Intern","Software Engineering Intern"][i%3],url=f"https://example.com/test-jobs/{i}",description="TEST FIXTURE. Paid internship building React and JavaScript interfaces. Required skills: React, JavaScript, TypeScript. Graduating 2028-2030. Requires 0 months experience. Work with the product team on accessible interfaces and customer-facing workflows.",location="Remote, India",remote_status="remote",compensation="INR 20,000/month",date_posted=datetime.now(timezone.utc)))
        return jobs[:limit]


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as directory:
        repo=LocalJsonRepository(Path(directory)/"test.json")
        asyncio.run(seed(repo))
        app.dependency_overrides[get_repository]=lambda:repo
        import app.pipeline.runner as runner
        runner.get_providers=lambda *_:[FixtureProvider()]
        uvicorn.run(app,host="127.0.0.1",port=8011)
