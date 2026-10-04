"""Optional bounded public-source verification; evidence is not a daily supply estimate."""
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import re
import socket
import tempfile
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup
from app.config import Settings
from app.models import CandidateProfile, DiscoveryRequest, SourceName
from app.pipeline.runner import run_discovery
from app.pipeline.scorer import score_job
from app.pipeline.urls import safe_public_url
from app.services.repository import LocalJsonRepository


async def check_link(job):
    url=job.url
    original_host=urlsplit(url).hostname
    result={'job_id':job.id,'company':job.company.name,'title':job.title,'source':job.source.value,'url':url}
    try:
        async with httpx.AsyncClient(timeout=8,follow_redirects=False,trust_env=False) as client:
            for _ in range(4):
                if not safe_public_url(url):
                    return result|{'status':'blocked_url'}
                p=urlsplit(url)
                addresses=await asyncio.to_thread(socket.getaddrinfo,p.hostname,p.port or (443 if p.scheme=='https' else 80),type=socket.SOCK_STREAM)
                if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
                    return result|{'status':'blocked_dns'}
                async with client.stream('GET',url,headers={'User-Agent':'InternshipIntelligenceBot/0.1 (bounded link verification)'}) as response:
                    if response.is_redirect:
                        next_url=urljoin(url,response.headers.get('location',''))
                        next_host=urlsplit(next_url).hostname
                        known_greenhouse={original_host,next_host} <= {'boards.greenhouse.io','job-boards.greenhouse.io'}
                        same_company=next_host and next_host.removeprefix('www.') == original_host.removeprefix('www.')
                        if next_host != original_host and not known_greenhouse and not same_company:
                            return result|{'status':'redirect_review','redirect':next_url}
                        url=next_url
                        continue
                    if response.status_code in (404,410):
                        return result|{'status':'dead','http':response.status_code}
                    if response.status_code in (401,403,429):
                        return result|{'status':'unverified_access_limit','http':response.status_code}
                    if not response.is_success:
                        return result|{'status':'unverified_http','http':response.status_code}
                    data=bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data)>1_000_000:
                            break
                    text=BeautifulSoup(bytes(data),'html.parser').get_text(' ',strip=True)
                    if re.search(r'job (?:is )?no longer available|position (?:has been |is )closed|job has expired|no longer accepting applications',text,re.I):
                        return result|{'status':'expired','http':response.status_code}
                    title_words={w.lower() for w in re.findall(r'[a-zA-Z]{4,}',job.title)}
                    overlap=title_words.intersection(text.lower().split())
                    company_present=job.company.name.lower() in text.lower()
                    return result|{'status':'corresponds' if len(overlap)>=2 and company_present else 'reachable_needs_review','http':response.status_code,'company_present':company_present,'title_overlap':sorted(overlap),'page_excerpt':text[:1200]}
            return result|{'status':'redirect_limit'}
    except Exception as exc:
        return result|{'status':'unverified_network','error_type':type(exc).__name__}


async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='data/live-v3.json')
    parser.add_argument('--limit',type=int,default=20)
    args=parser.parse_args()
    settings=Settings(_env_file=None,request_timeout_seconds=12)
    with tempfile.TemporaryDirectory() as directory:
        repo=LocalJsonRepository(Path(directory)/'jobs.json')
        # Explicit evaluation persona, not the user's stored private profile.
        profile=CandidateProfile(name='Frontend student evaluation persona',skills=['React','JavaScript','TypeScript','HTML','CSS','Git','Next.js'],preferred_roles=['frontend','full-stack','software engineering'],country='India',preferred_locations=['India'],education='B.Tech Computer Science',experience_months=3,paid_only=True,remote_preference=True)
        await repo.put_state('profile',profile.model_dump())
        individual=[]
        for source in SourceName:
            result=await run_discovery(settings,repo,DiscoveryRequest(sources=[source],limit_per_source=args.limit,persist=False))
            individual.extend(r.model_dump(mode='json') for r in result.source_report)
        combined=await run_discovery(settings,repo,DiscoveryRequest(limit_per_source=args.limit,persist=False))
        jobs=combined.jobs
        sample=[]
        for source in SourceName:
            sample.extend([j for j in jobs if j.source==source and j.opportunity_type=='internship'][:2])
        links=[]
        for job in sample:
            links.append(await check_link(job))
            await asyncio.sleep(1)
        active=[j for j in jobs if j.active and j.opportunity_type=='internship' and j.risk_state not in {'quarantined','blocked'}]
        evidence={'verified_at':datetime.now(timezone.utc).isoformat(),'limit':args.limit,'evaluation_profile':profile.model_dump(),'individual_reports':individual,'combined_reports':[r.model_dump(mode='json') for r in combined.source_report],'metrics':combined.metrics,'unique_active':len(active),'compensation_unknown':sum(j.compensation_status=='unknown' for j in active),'india_compatible':sum(j.country=='India' or j.worldwide_remote or 'India' in j.remote_countries for j in active),'priorities':dict(Counter(j.application_priority for j in active)),'link_sample':links,'jobs':[j.model_dump(mode='json') for j in jobs]}
        path=Path(args.output)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(evidence,indent=2))
        print(json.dumps({k:v for k,v in evidence.items() if k not in {'jobs','evaluation_profile','link_sample'}},indent=2))
        print('Link sample:',dict(Counter(l['status'] for l in links)))
        print('Evidence:',path.resolve())


if __name__=='__main__':
    asyncio.run(main())
