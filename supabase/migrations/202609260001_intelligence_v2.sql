begin;

-- URL paths may be case-sensitive; company websites are not unique identities.
drop index if exists public.jobs_url_unique_idx;
create unique index jobs_url_unique_idx on public.jobs(url);
drop index if exists public.companies_website_unique_idx;
create index if not exists companies_website_idx on public.companies(lower(website_url));

insert into public.job_sources(id, display_name, base_url) values
('simplify_jobs','SimplifyJobs','https://github.com/SimplifyJobs'),
('github_jobs','GitHub Trackers','https://github.com'),
('public_datasets','Program Catalog','https://github.com/deepanshu1422'),
('startup_career_pages','Greenhouse','https://boards-api.greenhouse.io')
on conflict(id) do nothing;

-- Preserve records and existing IDs. Extra extraction evidence can evolve independently.
alter table public.jobs add column if not exists intelligence jsonb not null default '{}';
alter table public.jobs add column if not exists normalized_title text not null default '';
alter table public.jobs add column if not exists role_family text not null default 'other';
alter table public.jobs add column if not exists country text;
alter table public.jobs add column if not exists opportunity_score integer not null default 0 check(opportunity_score between 0 and 100);
alter table public.jobs add column if not exists eligibility_score integer not null default 50 check(eligibility_score between 0 and 100);
alter table public.jobs add column if not exists active boolean not null default true;
alter table public.jobs add column if not exists deadline timestamptz;
alter table public.jobs add column if not exists favorite boolean not null default false;
alter table public.jobs add column if not exists hidden boolean not null default false;
alter table public.jobs add column if not exists stipend_min numeric;
alter table public.jobs add column if not exists compensation_currency text;
alter table public.jobs add column if not exists compensation_period text;
alter table public.jobs drop constraint if exists jobs_application_status_check;
alter table public.jobs add constraint jobs_application_status_check check(application_status in ('not_applied','planning','applied','assessment','interview','offer','rejected','withdrawn'));
alter table public.jobs add column if not exists search_document tsvector generated always as (
  to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,'') || ' ' || coalesce(location,''))
) stored;
create index if not exists jobs_search_idx on public.jobs using gin(search_document);
create index if not exists jobs_company_idx on public.jobs(company_id);
create index if not exists jobs_recommendations_idx on public.jobs(active, opportunity_score desc, id);
create index if not exists jobs_role_country_idx on public.jobs(role_family, country);
create index if not exists jobs_application_idx on public.jobs(application_status, favorite);
create index if not exists jobs_deadline_idx on public.jobs(deadline) where deadline is not null;
create index if not exists jobs_source_array_idx on public.jobs using gin(sources);
alter table public.discovery_runs add column if not exists details jsonb not null default '{}';
create index if not exists discovery_runs_started_idx on public.discovery_runs(started_at desc);

create table if not exists public.intelligence_state (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz not null default now()
);
comment on table public.intelligence_state is 'Private single-user profile, saved searches and AI cache. Requires owner-scoped tables before multi-user deployment.';

create or replace function public.touch_updated_at() returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;
drop trigger if exists jobs_updated_at on public.jobs;
create trigger jobs_updated_at before update on public.jobs for each row execute function public.touch_updated_at();
drop trigger if exists companies_updated_at on public.companies;
create trigger companies_updated_at before update on public.companies for each row execute function public.touch_updated_at();

create or replace function public.upsert_intelligence_jobs(payload jsonb) returns void
language plpgsql security invoker set search_path=public as $$
declare
  j jsonb; c jsonb; cid text; existing jsonb; merged jsonb;
begin
  for j in select value from jsonb_array_elements(payload) loop
    c := j->'company';
    select id into cid from companies where lower(name)=lower(c->>'name') limit 1;
    cid := coalesce(cid,c->>'id');
    insert into companies(id,name,website_url,linkedin_url,description,trust_score,suspicious,trust_reasons,excluded)
    values(cid,c->>'name',nullif(c->>'website_url',''),c->>'linkedin_url',c->>'description',
      (c->>'trust_score')::int,(c->>'suspicious')::boolean,array(select jsonb_array_elements_text(c->'trust_reasons')),(c->>'excluded')::boolean)
    on conflict(id) do update set
      description=coalesce(excluded.description,companies.description),
      trust_score=excluded.trust_score,suspicious=excluded.suspicious,
      trust_reasons=excluded.trust_reasons,excluded=companies.excluded or excluded.excluded;

    select jsonb_build_object('application_status',application_status,'favorite',favorite,
      'hidden',hidden,'notes',coalesce(notes,'')) || intelligence into existing
    from jobs where id=j->>'id' for update;
    merged := j;
    if existing is not null then
      merged := j || (select coalesce(jsonb_object_agg(key,value),'{}'::jsonb) from jsonb_each(existing)
        where key in ('application_status','applied_at','favorite','hidden','notes','interview_at','reminder_at','contact','corrections'));
    end if;
    insert into jobs(id,company_id,title,url,description,required_skills,preferred_skills,location,
      remote_status,compensation,compensation_status,source_platform,source_id,date_posted,date_discovered,
      first_seen,last_seen,sources,source_count,normalized_title,role_family,country,opportunity_score,
      eligibility_score,active,deadline,stipend_min,compensation_currency,compensation_period,
      application_status,favorite,hidden,notes,intelligence)
    values(j->>'id',cid,j->>'title',j->>'url',j->>'description',
      array(select jsonb_array_elements_text(j->'required_skills')),array(select jsonb_array_elements_text(j->'preferred_skills')),
      j->>'location',j->>'remote_status',j->>'compensation',j->>'compensation_status',j->>'source',j->>'source_id',
      (j->>'date_posted')::timestamptz,(j->>'date_discovered')::timestamptz,
      (j->>'first_seen')::timestamptz,(j->>'last_seen')::timestamptz,
      array(select jsonb_array_elements_text(j->'sources')),(j->>'source_count')::int,
      j->>'normalized_title',j->>'role_family',j->>'country',(j->>'opportunity_score')::int,
      (j->>'eligibility_score')::int,(j->>'active')::boolean,(j->>'deadline')::timestamptz,
      (j->>'stipend_min')::numeric,j->>'compensation_currency',j->>'compensation_period',
      coalesce(merged->>'application_status','not_applied'),coalesce((merged->>'favorite')::boolean,false),
      coalesce((merged->>'hidden')::boolean,false),coalesce(merged->>'notes',''),merged)
    on conflict(id) do update set title=excluded.title, description=excluded.description,
      required_skills=excluded.required_skills,preferred_skills=excluded.preferred_skills,
      location=excluded.location,remote_status=excluded.remote_status,compensation=excluded.compensation,
      compensation_status=excluded.compensation_status,last_seen=excluded.last_seen,
      sources=excluded.sources,source_count=excluded.source_count,normalized_title=excluded.normalized_title,
      role_family=excluded.role_family,country=excluded.country,opportunity_score=excluded.opportunity_score,
      eligibility_score=excluded.eligibility_score,active=excluded.active,deadline=excluded.deadline,
      stipend_min=excluded.stipend_min,compensation_currency=excluded.compensation_currency,
      compensation_period=excluded.compensation_period,intelligence=merged;
  end loop;
end;
$$;

create or replace function public.patch_intelligence_job(job_id text, changes jsonb) returns jsonb
language plpgsql security invoker set search_path=public as $$
declare result jsonb;
begin
  update jobs set intelligence=intelligence||changes,
    application_status=coalesce(changes->>'application_status',application_status),
    favorite=coalesce((changes->>'favorite')::boolean,favorite),
    hidden=coalesce((changes->>'hidden')::boolean,hidden),
    notes=coalesce(changes->>'notes',notes)
  where id=job_id;
  select to_jsonb(j)||jsonb_build_object('companies',to_jsonb(c)) into result
  from jobs j join companies c on j.company_id=c.id where j.id=job_id;
  return result;
end;
$$;

-- Backend service credentials only. No anonymous/private profile access.
alter table public.intelligence_state enable row level security;
alter table public.jobs enable row level security;
alter table public.companies enable row level security;
alter table public.raw_jobs enable row level security;
alter table public.discovery_runs enable row level security;
alter table public.company_exclusions enable row level security;
alter table public.job_skills enable row level security;
alter table public.trust_scores enable row level security;
alter table public.tags enable row level security;
alter table public.job_sources enable row level security;
revoke all on public.intelligence_state,public.jobs,public.companies,public.raw_jobs,
  public.discovery_runs,public.company_exclusions,public.job_skills,public.trust_scores,
  public.tags,public.job_sources from anon, authenticated;
grant all on public.intelligence_state,public.jobs,public.companies,public.raw_jobs,
  public.discovery_runs,public.company_exclusions,public.job_skills,public.trust_scores,
  public.tags,public.job_sources to service_role;
revoke all on function public.upsert_intelligence_jobs(jsonb) from public, anon, authenticated;
revoke all on function public.patch_intelligence_job(text,jsonb) from public, anon, authenticated;
grant execute on function public.upsert_intelligence_jobs(jsonb) to service_role;
grant execute on function public.patch_intelligence_job(text,jsonb) to service_role;
commit;
