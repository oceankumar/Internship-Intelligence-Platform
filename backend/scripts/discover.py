"""Scheduler-compatible entry point using the same durable lease as manual discovery."""
import argparse
import asyncio
import json
from app.config import Settings
from app.models import DiscoveryRequest
from app.pipeline.runner import run_discovery
from app.services.repository import make_repository


async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--limit',type=int,default=20)
    args=parser.parse_args()
    settings=Settings()
    result=await run_discovery(settings,make_repository(settings),DiscoveryRequest(limit_per_source=args.limit,persist=not args.dry_run))
    print(json.dumps({'run_id':result.run_id,'metrics':result.metrics,'reports':[r.model_dump() for r in result.source_report]},indent=2))


if __name__=='__main__':
    asyncio.run(main())
