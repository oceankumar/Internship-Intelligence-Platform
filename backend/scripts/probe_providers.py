"""Bounded read-only live probe; never writes to the application database."""
import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings
from app.models import DiscoveryRequest, SourceName
from app.pipeline.runner import run_discovery
from app.services.repository import LocalJsonRepository


async def main():
    with tempfile.TemporaryDirectory() as directory:
        result = await run_discovery(Settings(_env_file=None,request_timeout_seconds=12), LocalJsonRepository(Path(directory)/"jobs.json"), DiscoveryRequest(sources=list(SourceName),limit_per_source=20,persist=False))
        print(json.dumps({"probed_at":datetime.now(timezone.utc).isoformat(),"limit_per_source":20,"query":"internship","reports":[r.model_dump() for r in result.source_report],"metrics":result.metrics,"returned_jobs":len(result.jobs)},indent=2))


if __name__ == "__main__":
    asyncio.run(main())
