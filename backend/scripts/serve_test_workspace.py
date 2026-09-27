"""Isolated browser-test workspace; fixtures never enter the real data store."""
import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from app.main import app, get_repository
from app.models import CandidateProfile, Company, Job
from app.services.repository import LocalJsonRepository


async def seed(repo):
    await repo.put_state("profile",CandidateProfile(name="Test Candidate",skills=["react","javascript","html","css"],country="India",graduation_year=2029,experience_months=3).model_dump())
    jobs=[]
    for i in range(16):
        jobs.append(Job(company=Company(name=["Test Acme","Test Studio","Test Research"][i%3]),title=["Frontend Engineering Intern","Product Design Intern","Software Engineering Intern"][i%3],url=f"https://example.com/test-jobs/{i}",source="yc_jobs",description="TEST FIXTURE. Paid internship building React and JavaScript interfaces. Graduating 2028-2030. Requires 0 months experience. Work with the product team on accessible interfaces and customer-facing workflows.",required_skills=["react","javascript","typescript"],location="Remote, India",remote_status="remote",compensation="INR 20,000/month",compensation_status="paid",date_posted=datetime.now(timezone.utc)))
    await repo.upsert_jobs(jobs)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as directory:
        repo=LocalJsonRepository(Path(directory)/"test.json")
        asyncio.run(seed(repo))
        app.dependency_overrides[get_repository]=lambda:repo
        uvicorn.run(app,host="127.0.0.1",port=8011)
