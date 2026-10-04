"""Immutable public-source snapshot, isolated from every owner data store."""
import json
from copy import deepcopy
from pathlib import Path

from app.models import Job
from app.services.repository import Repository


class DemoRepository(Repository):
    def __init__(self):
        self.snapshot = json.loads((Path(__file__).parents[2] / "demo/snapshot.json").read_text())

    async def list_jobs(self):
        return [Job.model_validate(j) for j in self.snapshot["jobs"]]

    async def get_state(self, key, default=None):
        if key == "profile":
            return deepcopy(self.snapshot["profile"])
        return deepcopy(default)

    async def list_runs(self):
        return deepcopy(self.snapshot["runs"])

    async def put_state(self, key, value):
        raise PermissionError("Public demo is read-only")

    async def patch_job(self, job_id, changes):
        raise PermissionError("Public demo is read-only")

    async def upsert_jobs(self, jobs):
        raise PermissionError("Public demo is read-only")
