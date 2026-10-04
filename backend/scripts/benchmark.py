"""Synthetic measurement only; never mutates application storage."""
from time import perf_counter
import json
import resource
from app.models import Job, Company, CandidateProfile
from app.pipeline.dedupe import merge_jobs
from app.pipeline.scorer import score_job
from app.services.search import filter_jobs, sort_jobs, Filters


def main():
    output=[]
    for count in (1000,5000,10000):
        jobs=[Job(id=str(i),company=Company(name=f'Benchmark {i}'),title='Frontend Intern',url=f'https://example.com/jobs/{i}',source='yc_jobs',description='React required. Paid internship. Remote, India.',required_skills=['react'],location='Remote, India',compensation_status='paid',remote_status='remote') for i in range(count)]
        profile=CandidateProfile(skills=['react'],country='India')
        t=perf_counter()
        for job in jobs: score_job(job,profile)
        ranking=perf_counter()-t
        t=perf_counter();filtered=filter_jobs(jobs,Filters(role='frontend'));filter_time=perf_counter()-t
        t=perf_counter();page=sort_jobs(filtered,'recommended')[:20];listing=perf_counter()-t
        t=perf_counter();merged,metrics=merge_jobs(jobs,[j.model_copy() for j in jobs[:100]]);dedupe=perf_counter()-t
        output.append({'jobs':count,'ranking_seconds':round(ranking,3),'filter_seconds':round(filter_time,3),'sort_pagination_seconds':round(listing,3),'dedupe_100_seconds':round(dedupe,3),'max_rss_platform_units':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    print(json.dumps(output,indent=2))


if __name__=='__main__':main()
