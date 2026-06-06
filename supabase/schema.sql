create extension if not exists pgcrypto;

create table if not exists companies (
  id text primary key,
  name text not null,
  website_url text,
  linkedin_url text,
  description text,
  trust_score integer not null default 0 check (trust_score between 0 and 100),
  suspicious boolean not null default false,
  trust_reasons text[] not null default '{}',
  excluded boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists companies_name_unique_idx on companies (lower(name));
create unique index if not exists companies_website_unique_idx on companies (lower(website_url)) where website_url is not null;

create table if not exists job_sources (
  id text primary key,
  display_name text not null,
  base_url text not null,
  enabled boolean not null default true,
  created_at timestamptz not null default now()
);

insert into job_sources (id, display_name, base_url)
values
  ('remoteok', 'RemoteOK', 'https://remoteok.com'),
  ('yc_jobs', 'Y Combinator Jobs', 'https://www.ycombinator.com/jobs'),
  ('work_at_a_startup', 'Work at a Startup', 'https://www.workatastartup.com/jobs'),
  ('wellfound', 'Wellfound', 'https://wellfound.com/jobs')
on conflict (id) do update set
  display_name = excluded.display_name,
  base_url = excluded.base_url;

create table if not exists jobs (
  id text primary key,
  company_id text not null references companies(id) on delete cascade,
  title text not null,
  url text not null,
  description text not null default '',
  required_skills text[] not null default '{}',
  preferred_skills text[] not null default '{}',
  location text,
  remote_status text not null default 'unknown' check (remote_status in ('remote', 'hybrid', 'onsite', 'unknown')),
  internship_type text not null default 'internship',
  compensation text,
  compensation_status text not null default 'unknown' check (compensation_status in ('paid', 'unpaid', 'unknown')),
  source_platform text not null references job_sources(id),
  source_id text,
  date_posted timestamptz,
  date_discovered timestamptz not null default now(),
  relevance_score integer not null default 0 check (relevance_score between 0 and 100),
  score_reasons text[] not null default '{}',
  tags text[] not null default '{}',
  suspicious boolean not null default false,
  archived boolean not null default false,
  status text not null default 'new' check (status in ('new', 'saved', 'ignored', 'applied_later', 'archived')),
  notes text,
  first_seen timestamptz not null default now(),
  last_seen timestamptz not null default now(),
  sources text[] not null default '{}',
  source_count integer not null default 1,
  match_score integer not null default 0 check (match_score between 0 and 100),
  application_priority text not null default 'Low Priority' check (application_priority in ('Apply Today', 'Apply This Week', 'Low Priority')),
  application_status text not null default 'not_applied' check (application_status in ('not_applied', 'applied', 'interview', 'rejected', 'offer')),
  match_reasons text[] not null default '{}',
  matching_skills text[] not null default '{}',
  missing_skills text[] not null default '{}',
  days_since_seen integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists jobs_url_unique_idx on jobs (lower(url));
create unique index if not exists jobs_source_unique_idx on jobs (source_platform, source_id) where source_id is not null;
create index if not exists jobs_relevance_idx on jobs (relevance_score desc);
create index if not exists jobs_date_discovered_idx on jobs (date_discovered desc);
create index if not exists jobs_tags_gin_idx on jobs using gin (tags);
create index if not exists jobs_required_skills_gin_idx on jobs using gin (required_skills);

create table if not exists job_skills (
  job_id text not null references jobs(id) on delete cascade,
  skill text not null,
  skill_type text not null check (skill_type in ('required', 'preferred')),
  primary key (job_id, skill, skill_type)
);

create table if not exists trust_scores (
  id uuid primary key default gen_random_uuid(),
  company_id text not null references companies(id) on delete cascade,
  score integer not null check (score between 0 and 100),
  reasons text[] not null default '{}',
  evaluated_at timestamptz not null default now()
);

create table if not exists tags (
  id text primary key,
  label text not null unique,
  created_at timestamptz not null default now()
);

create table if not exists company_exclusions (
  company_id text primary key references companies(id) on delete cascade,
  reason text,
  created_at timestamptz not null default now()
);

create table if not exists discovery_runs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  status text not null check (status in ('running', 'completed', 'failed')),
  query text,
  limit_per_source integer,
  stored_count integer,
  discovered_count integer,
  errors jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists raw_jobs (
  id text primary key,
  run_id uuid references discovery_runs(id) on delete cascade,
  source_platform text not null,
  source_id text,
  url text not null,
  company_name text not null,
  title text not null,
  raw_data jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists raw_jobs_run_id_idx on raw_jobs (run_id);
create index if not exists raw_jobs_source_platform_idx on raw_jobs (source_platform);


