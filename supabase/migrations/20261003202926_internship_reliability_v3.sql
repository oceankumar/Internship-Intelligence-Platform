begin;

-- Generic careers URLs are not unique job identities.
drop index if exists public.jobs_url_unique_idx;
create index if not exists jobs_url_idx on public.jobs(url);
alter table public.jobs drop constraint if exists jobs_application_priority_check;
alter table public.jobs add constraint jobs_application_priority_check check(application_priority in
 ('Apply Today','Apply This Week','Low Priority','Apply Now','Strong Match','Worth Exploring','Low Match','Hidden / Rejected'));
alter table public.discovery_runs drop constraint if exists discovery_runs_status_check;
alter table public.discovery_runs add constraint discovery_runs_status_check check(status in
 ('running','completed','completed_with_warnings','degraded','failed','cancelled'));
alter table public.jobs add column if not exists trust_score integer not null default 0 check(trust_score between 0 and 100);
alter table public.jobs add column if not exists risk_state text not null default 'review' check(risk_state in ('normal','review','quarantined','blocked'));
alter table public.jobs add column if not exists listing_risk_score integer not null default 0 check(listing_risk_score between 0 and 100);
alter table public.jobs add column if not exists evidence_confidence integer not null default 0 check(evidence_confidence between 0 and 100);
alter table public.jobs add column if not exists fit_score integer check(fit_score between 0 and 100);
alter table public.jobs add column if not exists stipend_max numeric;
alter table public.jobs add column if not exists opportunity_type text not null default 'internship';
alter table public.jobs add column if not exists application_state text not null default 'unknown' check(application_state in ('open','closed','unknown'));
create index if not exists jobs_safe_recommendations_idx on public.jobs(active, risk_state, opportunity_score desc, id);
comment on column public.companies.trust_score is 'Company identity evidence, not a probability or listing risk score.';
comment on column public.job_sources.enabled is 'Legacy metadata only. Runtime operator authority is ENABLED_SOURCES.';

create table if not exists public.job_source_instances (
 provider text not null references public.job_sources(id),
 provider_job_id text not null,
 job_id text not null references public.jobs(id) on delete cascade,
 canonical_apply_url text,
 tracker_url text,
 requisition_id text,
 primary key(provider,provider_job_id)
);
create index if not exists job_source_instances_job_idx on public.job_source_instances(job_id);
alter table public.job_source_instances enable row level security;
revoke all on public.job_source_instances from anon,authenticated;
grant all on public.job_source_instances to service_role;

-- Ingestion writes evidence JSON and synchronizes typed ranking columns in the same row.
-- Readers treat typed columns as authoritative; personal tracker columns remain separate.
create or replace function public.sync_listing_intelligence() returns trigger
language plpgsql set search_path=public as $$
declare j jsonb := new.intelligence;
begin
 new.match_score := coalesce((j->>'match_score')::int,new.match_score);
 new.relevance_score := coalesce((j->>'relevance_score')::int,new.relevance_score);
 new.application_priority := coalesce(j->>'application_priority',new.application_priority);
 new.trust_score := coalesce((j->>'trust_score')::int,new.trust_score);
 new.risk_state := coalesce(j->>'risk_state',new.risk_state);
 new.listing_risk_score := coalesce((j->>'listing_risk_score')::int,new.listing_risk_score);
 new.evidence_confidence := coalesce((j->>'evidence_confidence')::int,new.evidence_confidence);
 if j ? 'fit_score' then new.fit_score := (j->>'fit_score')::int; end if;
 new.stipend_max := coalesce((j->>'stipend_max')::numeric,new.stipend_max);
 new.opportunity_type := coalesce(j->>'opportunity_type',new.opportunity_type);
 new.application_state := coalesce(j->>'application_state',new.application_state);
 new.suspicious := coalesce((j->>'suspicious')::boolean,new.suspicious);
 if j ? 'match_reasons' then new.match_reasons := array(select jsonb_array_elements_text(j->'match_reasons')); end if;
 if j ? 'matching_skills' then new.matching_skills := array(select jsonb_array_elements_text(j->'matching_skills')); end if;
 if j ? 'missing_skills' then new.missing_skills := array(select jsonb_array_elements_text(j->'missing_skills')); end if;
 return new;
end;
$$;
drop trigger if exists jobs_sync_intelligence on public.jobs;
create trigger jobs_sync_intelligence before insert or update of intelligence on public.jobs
for each row execute function public.sync_listing_intelligence();
update public.jobs set intelligence=intelligence where intelligence <> '{}';

create or replace function public.record_listing_instances() returns trigger
language plpgsql set search_path=public as $$
declare s jsonb;
begin
 for s in select value from jsonb_array_elements(coalesce(new.intelligence->'source_instances','[]')) loop
  if nullif(s->>'provider_job_id','') is not null then
   insert into job_source_instances(provider,provider_job_id,job_id,canonical_apply_url,tracker_url,requisition_id)
   values(s->>'provider',s->>'provider_job_id',new.id,s->>'canonical_apply_url',s->>'tracker_url',s->>'requisition_id')
   on conflict(provider,provider_job_id) do update set canonical_apply_url=excluded.canonical_apply_url,
    tracker_url=excluded.tracker_url,requisition_id=excluded.requisition_id
   where job_source_instances.job_id=excluded.job_id;
  end if;
 end loop;
 return new;
end;
$$;
drop trigger if exists jobs_record_instances on public.jobs;
create trigger jobs_record_instances after insert or update of intelligence on public.jobs
for each row execute function public.record_listing_instances();

create or replace function public.acquire_discovery_lease(owner text,seconds integer) returns boolean
language plpgsql security invoker set search_path=public as $$
declare acquired text;
begin
 if seconds < 180 or seconds > 3600 then raise exception 'Invalid lease duration'; end if;
 insert into intelligence_state(key,value) values('discovery_lease',jsonb_build_object('owner',owner,'expires',now()+make_interval(secs=>seconds)))
 on conflict(key) do update set value=excluded.value,updated_at=now()
 where (intelligence_state.value->>'expires')::timestamptz <= now()
 returning value->>'owner' into acquired;
 return acquired=owner and acquired is not null;
end;
$$;
create or replace function public.release_discovery_lease(owner text) returns void
language plpgsql security invoker set search_path=public as $$
begin
 delete from intelligence_state where key='discovery_lease' and value->>'owner'=owner;
end;
$$;

create or replace function public.complete_intelligence_discovery(payload jsonb,raw_payload jsonb,run_payload jsonb) returns void
language plpgsql security invoker set search_path=public as $$
begin
 perform upsert_intelligence_jobs(payload);
 insert into raw_jobs(id,run_id,source_platform,source_id,url,company_name,title,raw_data)
 select id,run_id,source_platform,source_id,url,company_name,title,raw_data
 from jsonb_to_recordset(raw_payload) as r(id text,run_id uuid,source_platform text,source_id text,url text,company_name text,title text,raw_data jsonb);
 update discovery_runs set status=run_payload->>'status',completed_at=(run_payload->>'completed_at')::timestamptz,
 stored_count=(run_payload->>'stored_count')::int,discovered_count=(run_payload->>'discovered_count')::int,
 errors=coalesce(run_payload->'errors','{}'),details=run_payload
 where id=(run_payload->>'id')::uuid and status='running';
 if not found then raise exception 'Missing running discovery run'; end if;
end;
$$;
revoke all on function public.acquire_discovery_lease(text,integer),public.release_discovery_lease(text),public.complete_intelligence_discovery(jsonb,jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.acquire_discovery_lease(text,integer),public.release_discovery_lease(text),public.complete_intelligence_discovery(jsonb,jsonb,jsonb) to service_role;
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
      website_url=coalesce(excluded.website_url,companies.website_url),
      linkedin_url=coalesce(excluded.linkedin_url,companies.linkedin_url),
      trust_score=excluded.trust_score,suspicious=excluded.suspicious,
      trust_reasons=excluded.trust_reasons,excluded=companies.excluded or excluded.excluded;

    select intelligence || jsonb_build_object('application_status',application_status,'favorite',favorite,
      'hidden',hidden,'notes',coalesce(notes,'')) into existing
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
commit;
