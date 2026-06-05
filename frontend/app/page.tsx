"use client";

import { AlertTriangle, Download, ExternalLink, RefreshCw, Search, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { exportUrl, fetchJobs, Job, runDiscovery } from "../lib/api";

type Filter = "all" | "paid" | "remote" | "suspicious";

export default function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadJobs() {
    setLoading(true);
    setError(null);
    try {
      setJobs(await fetchJobs());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load internships");
    } finally {
      setLoading(false);
    }
  }

  async function handleDiscovery() {
    setRunning(true);
    setError(null);
    try {
      const result = await runDiscovery();
      setJobs(result.jobs.length ? result.jobs : await fetchJobs());
      if (Object.keys(result.errors).length) {
        setError(`Some sources failed: ${Object.keys(result.errors).join(", ")}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Discovery failed");
    } finally {
      setRunning(false);
    }
  }

  useEffect(() => {
    loadJobs();
  }, []);

  const filtered = useMemo(() => {
    return jobs.filter((job) => {
      if (filter === "paid") return job.compensation_status === "paid";
      if (filter === "remote") return job.remote_status === "remote";
      if (filter === "suspicious") return job.suspicious;
      return true;
    });
  }, [filter, jobs]);

  const metrics = useMemo(() => {
    return {
      total: jobs.length,
      paid: jobs.filter((job) => job.compensation_status === "paid").length,
      remote: jobs.filter((job) => job.remote_status === "remote").length,
      suspicious: jobs.filter((job) => job.suspicious).length,
      averageScore: jobs.length ? Math.round(jobs.reduce((sum, job) => sum + job.relevance_score, 0) / jobs.length) : 0
    };
  }, [jobs]);

  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">Phase 1 discovery system</p>
          <h1>Internship Intelligence</h1>
        </div>
        <div className="actions">
          <a className="iconButton" href={exportUrl("csv")} title="Export CSV">
            <Download size={18} />
            CSV
          </a>
          <a className="iconButton" href={exportUrl("xlsx")} title="Export Excel">
            <Download size={18} />
            Excel
          </a>
          <button className="primaryButton" onClick={handleDiscovery} disabled={running}>
            {running ? <RefreshCw className="spin" size={18} /> : <Search size={18} />}
            {running ? "Scanning" : "Run discovery"}
          </button>
        </div>
      </section>

      <section className="metrics" aria-label="Dashboard metrics">
        <Metric label="Total" value={metrics.total} />
        <Metric label="Paid" value={metrics.paid} />
        <Metric label="Remote" value={metrics.remote} />
        <Metric label="Avg score" value={metrics.averageScore} />
        <Metric label="Flagged" value={metrics.suspicious} tone="warn" />
      </section>

      <section className="workspace">
        <aside className="sidebar">
          <div className="panelTitle">
            <Sparkles size={18} />
            Profile Match
          </div>
          <p className="profileText">
            Frontend-first CS and AI student targeting paid React, Next.js, web, full-stack, and startup engineering internships.
          </p>
          <div className="filters">
            {(["all", "paid", "remote", "suspicious"] as Filter[]).map((item) => (
              <button key={item} className={filter === item ? "filter active" : "filter"} onClick={() => setFilter(item)}>
                {item}
              </button>
            ))}
          </div>
          {error ? <div className="error">{error}</div> : null}
        </aside>

        <section className="results">
          {loading ? (
            <div className="emptyState">Loading internships...</div>
          ) : filtered.length ? (
            filtered.map((job) => <JobRow key={job.id || job.url} job={job} />)
          ) : (
            <div className="emptyState">No internships match this view.</div>
          )}
        </section>
      </section>
    </main>
  );
}

function Metric({ label, value, tone }: { label: string; value: number; tone?: "warn" }) {
  return (
    <div className={tone === "warn" ? "metric warn" : "metric"}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function JobRow({ job }: { job: Job }) {
  const scoreClass = job.relevance_score >= 80 ? "good" : job.relevance_score >= 55 ? "mid" : "low";
  return (
    <article className="jobRow">
      <div className="scoreBlock">
        <span className={`score ${scoreClass}`}>{job.relevance_score}</span>
        <span>match</span>
      </div>
      <div className="jobMain">
        <div className="jobHeader">
          <div>
            <h2>{job.title}</h2>
            <p>{job.company.name}</p>
          </div>
          <a href={job.url} target="_blank" rel="noreferrer" className="openLink" title="Open internship">
            <ExternalLink size={18} />
          </a>
        </div>
        <div className="chips">
          <span>{job.source}</span>
          <span>{job.remote_status}</span>
          <span>{job.compensation_status}</span>
          {job.location ? <span>{job.location}</span> : null}
        </div>
        <p className="description">{job.description || "No description collected yet."}</p>
        <div className="skillLine">
          {job.required_skills.slice(0, 6).map((skill) => (
            <span key={skill}>{skill}</span>
          ))}
        </div>
        <div className="reasons">
          {job.score_reasons.slice(0, 3).map((reason) => (
            <span key={reason}>{reason}</span>
          ))}
        </div>
      </div>
      <div className="trustBlock">
        {job.suspicious ? <AlertTriangle size={18} /> : <ShieldCheck size={18} />}
        <strong>{job.company.trust_score}</strong>
        <span>{job.suspicious ? "review" : "trusted"}</span>
      </div>
    </article>
  );
}

