import Link from "next/link";

export default function About() {
  return <main className="page-content">
    <Link href="/">Back to InternAI</Link>
    <header className="page-heading"><div><h1>InternAI</h1><p>Internship Intelligence Platform</p></div></header>
    <section><h2>From public sources to explainable decisions</h2><p>Public job feeds and employer boards → provider adapters → normalization and skill extraction → deduplication, eligibility and listing-risk checks → deterministic candidate ranking → FastAPI → Next.js.</p></section>
    <section><h2>Engineering boundaries</h2><p>Ranking uses explicit weights, evidence completeness and eligibility constraints. Optional schema-validated LLM classification can help interpret descriptions; it never supplies the numerical match score.</p><p>The public demo reads a timestamped, sanitized snapshot of real public listings. It contains no private resume, notes, contacts or application history. Search and exports work; shared writes and discovery are disabled.</p><p>The private workspace supports profile editing, application tracking, corrections and discovery. Its Supabase PostgreSQL adapter has migration and repository tests; hosted persistence is not certified without a hosted verification run.</p></section>
    <section><h2>Source reliability</h2><p>Six enabled source types include RemoteOK, public YC Jobs, Simplify and GitHub trackers, Greenhouse employer boards and a separately classified program catalog. Restricted sources stay disabled. Source success is not a promise of useful daily supply.</p></section>
    <a href="https://github.com/oceankumar/Internship-Intelligence-Platform" target="_blank" rel="noreferrer">Source code and architecture</a>
  </main>;
}
