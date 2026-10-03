import { PGlite } from "@electric-sql/pglite";
import { pgcrypto } from "@electric-sql/pglite/contrib/pgcrypto";
import { readFile } from "node:fs/promises";
import assert from "node:assert/strict";

const db = new PGlite({ extensions: { pgcrypto } });
await db.exec(
  "create role anon; create role authenticated; create role service_role bypassrls;",
);
await db.exec(
  await readFile(new URL("../../supabase/schema.sql", import.meta.url), "utf8"),
);
await db.exec(
  "insert into companies(id,name) values('legacy','Legacy'); insert into jobs(id,company_id,title,url,source_platform,application_status,notes) values('legacy','legacy','Frontend Intern','https://example.com/legacy','yc_jobs','applied','Keep my notes');",
);
const migration = await readFile(
  new URL(
    "../../supabase/migrations/202609260001_intelligence_v2.sql",
    import.meta.url,
  ),
  "utf8",
);
await db.exec(migration);
await db.exec(migration);
const v3 = await readFile(new URL('../../supabase/migrations/20261003202926_internship_reliability_v3.sql', import.meta.url), 'utf8');
await db.exec(v3);
await db.exec(v3);
const job = {
  id: "legacy",
  company: {
    id: "legacy",
    name: "Legacy",
    website_url: null,
    linkedin_url: null,
    description: null,
    trust_score: 70,
    suspicious: false,
    trust_reasons: [],
    excluded: false,
  },
  title: "Frontend Intern",
  url: "https://example.com/legacy",
  description: "React internship",
  required_skills: ["react"],
  preferred_skills: [],
  location: "India",
  remote_status: "remote",
  compensation: null,
  compensation_status: "unknown",
  source: "yc_jobs",
  source_id: "legacy",
  date_posted: null,
  date_discovered: new Date().toISOString(),
  first_seen: new Date().toISOString(),
  last_seen: new Date().toISOString(),
  sources: ["yc_jobs"],
  source_count: 1,
  normalized_title: "frontend intern",
  role_family: "frontend",
  country: "India",
  opportunity_score: 75,
  eligibility_score: 60,
  active: true,
  deadline: null,
  stipend_min: null,
  compensation_currency: null,
  compensation_period: null,
  application_status: "not_applied",
  favorite: false,
  hidden: false,
  notes: "",
  match_score: 81,
  application_priority: 'Strong Match',
  risk_state: 'normal',
  trust_score: 65,
  evidence_confidence: 80,
  source_instances: [{provider:'yc_jobs',provider_job_id:'legacy',canonical_apply_url:'https://example.com/legacy'}],
};
await db.query("select upsert_intelligence_jobs($1::jsonb)", [
  JSON.stringify([job]),
]);
let saved = (await db.query("select * from jobs where id='legacy'")).rows[0];
assert.equal(saved.application_status, "applied");
assert.equal(saved.intelligence.notes, "Keep my notes");
await db.query("select patch_intelligence_job('legacy',$1::jsonb)", [
  JSON.stringify({
    notes: "Updated note",
    application_status: "interview",
    favorite: true,
  }),
]);
await db.query("select upsert_intelligence_jobs($1::jsonb)", [
  JSON.stringify([job]),
]);
saved = (await db.query("select * from jobs where id='legacy'")).rows[0];
assert.equal(saved.intelligence.notes, "Updated note");
assert.equal(saved.application_status, "interview");
assert.equal(saved.favorite, true);
assert.ok(saved.search_document.includes("react"));
assert.equal(saved.match_score,81);
assert.equal(saved.application_priority,'Strong Match');
assert.equal(saved.trust_score,65);
assert.equal((await db.query('select count(*)::int as n from job_source_instances')).rows[0].n,1);
assert.equal((await db.query("select acquire_discovery_lease('a',900) as ok")).rows[0].ok,true);
assert.equal((await db.query("select acquire_discovery_lease('b',900) as ok")).rows[0].ok,false);
await db.query("select release_discovery_lease('b')");
assert.equal((await db.query("select acquire_discovery_lease('b',900) as ok")).rows[0].ok,false);
await db.query("select release_discovery_lease('a')");
assert.equal((await db.query("select acquire_discovery_lease('b',900) as ok")).rows[0].ok,true);
await assert.rejects(db.query('select complete_intelligence_discovery($1, $2, $3)',[JSON.stringify([{...job,id:'rollback',source_id:'rollback',source_instances:[],url:'https://example.com/rollback'}]),'[]',JSON.stringify({id:'00000000-0000-0000-0000-000000000001',status:'completed'})]),/Missing running/);
assert.equal((await db.query("select count(*)::int as n from jobs where id='rollback'")).rows[0].n,0);
await db.query("insert into discovery_runs(id,status) values('00000000-0000-0000-0000-000000000002','running')");
await db.query('select complete_intelligence_discovery($1,$2,$3)',[
  JSON.stringify([job]),JSON.stringify([{id:'raw-test',run_id:'00000000-0000-0000-0000-000000000002',source_platform:'yc_jobs',url:job.url,company_name:'Legacy',title:job.title,raw_data:{fixture:true}}]),
  JSON.stringify({id:'00000000-0000-0000-0000-000000000002',status:'completed_with_warnings',stored_count:0,discovered_count:1,completed_at:new Date().toISOString(),metrics:{active:1}})
]);
assert.equal((await db.query("select status from discovery_runs where id='00000000-0000-0000-0000-000000000002'")).rows[0].status,'completed_with_warnings');
assert.equal((await db.query('select count(*)::int as n from raw_jobs')).rows[0].n,1);
await db.exec("set role anon");
await assert.rejects(
  db.query("select * from intelligence_state"),
  /permission denied/,
);
await assert.rejects(
  db.query("select patch_intelligence_job('legacy','{}')"),
  /permission denied/,
);
await db.exec("reset role; set role service_role");
assert.equal(
  (await db.query("select count(*)::int as n from jobs")).rows[0].n,
  1,
);
await db.exec("reset role");
const tables = (
  await db.query(
    "select relname from pg_class where relnamespace='public'::regnamespace and relkind='r' and not relrowsecurity",
  )
).rows;
assert.deepEqual(tables, []);
await db.close();
console.log(
  "PASS: schema + repeatable migration, legacy preservation, RPC round-trip, RLS/grants, service-role access",
);
