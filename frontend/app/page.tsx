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
    const newToday = jobs.filter((job) => job.is_new).length;
    const newThisWeek = jobs.filter((job) => job.days_since_seen <= 7).length;
    const updatedThisWeek = jobs.filter((job) => job.source_count > 1 && job.days_since_seen <= 7).length;
    const topMatches = jobs.filter((job) => job.match_score >= 85).length;
    const highPriority = jobs.filter((job) => job.application_priority === "Apply Today").length;

    return {
      total: jobs.length,
      newToday,
      newThisWeek,
      updatedThisWeek,
      topMatches,
      highPriority,
      suspicious: jobs.filter((job) => job.suspicious).length,
      averageStipend: (() => {
        const parsedStipends = jobs
          .map((job) => {
            if (!job.compensation) return null;
            const str = job.compensation.toLowerCase();
            if (str.includes("unpaid") || str.includes("no stipend")) return null;
            
            const cleanStr = str.replace(/,/g, '');
            const numbers = cleanStr.match(/\d+(\.\d+)?/g);
            if (!numbers || numbers.length === 0) return null;
            
            let amount = 0;
            if (numbers.length >= 2) {
              amount = (parseFloat(numbers[0]) + parseFloat(numbers[1])) / 2;
            } else {
              amount = parseFloat(numbers[0]);
            }
            
            let period = "month";
            if (cleanStr.includes("hour") || cleanStr.includes("hr")) {
              period = "hour";
            } else if (cleanStr.includes("year") || cleanStr.includes("yr") || cleanStr.includes("annual")) {
              period = "year";
            } else if (cleanStr.includes("week") || cleanStr.includes("wk")) {
              period = "week";
            }
            
            let isUSD = true;
            if (cleanStr.includes("₹") || cleanStr.includes("inr") || cleanStr.includes("rs") || cleanStr.includes("rupee")) {
              isUSD = false;
            }
            
            let monthlyAmount = amount;
            if (period === "hour") {
              monthlyAmount = amount * 160;
            } else if (period === "year") {
              monthlyAmount = amount / 12;
            } else if (period === "week") {
              monthlyAmount = amount * 4;
            }
            
            return { amount: monthlyAmount, isUSD };
          })
          .filter((x): x is { amount: number; isUSD: boolean } => x !== null);

        const usdStipends = parsedStipends.filter(s => s.isUSD).map(s => s.amount);
        const inrStipends = parsedStipends.filter(s => !s.isUSD).map(s => s.amount);

        if (usdStipends.length > 0 && inrStipends.length > 0) {
          const avgUsd = Math.round(usdStipends.reduce((a, b) => a + b, 0) / usdStipends.length);
          const avgInr = Math.round(inrStipends.reduce((a, b) => a + b, 0) / inrStipends.length);
          const formattedInr = avgInr >= 1000 ? `${Math.round(avgInr / 1000)}k` : `${avgInr}`;
          return `$${avgUsd} / ₹${formattedInr}`;
        } else if (usdStipends.length > 0) {
          const avgUsd = Math.round(usdStipends.reduce((a, b) => a + b, 0) / usdStipends.length);
          return `$${avgUsd}/mo`;
        } else if (inrStipends.length > 0) {
          const avgInr = Math.round(inrStipends.reduce((a, b) => a + b, 0) / inrStipends.length);
          if (avgInr >= 1000) {
            return `₹${Math.round(avgInr / 1000)}k/mo`;
          } else {
            return `₹${avgInr}/mo`;
          }
        }
        return "N/A";
      })()
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
        <Metric label="Total Internships" value={metrics.total} />
        <Metric label="New Today" value={metrics.newToday} />
        <Metric label="New This Week" value={metrics.newThisWeek} />
        <Metric label="Updated This Week" value={metrics.updatedThisWeek} />
        <Metric label="Top Matches" value={metrics.topMatches} />
        <Metric label="High Priority" value={metrics.highPriority} />
        <Metric label="Avg Stipend" value={metrics.averageStipend} />
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

function Metric({ label, value, tone }: { label: string; value: number | string; tone?: "warn" }) {
  return (
    <div className={tone === "warn" ? "metric warn" : "metric"}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function JobRow({ job }: { job: Job }) {
  const [expanded, setExpanded] = useState(false);
  const scoreClass = job.match_score >= 80 ? "good" : job.match_score >= 60 ? "mid" : "low";
  
  const sourcesList = job.sources && job.sources.length > 0 ? job.sources : [job.source];
  
  return (
    <article 
      className={`jobRow ${expanded ? 'expanded' : ''}`} 
      onClick={() => setExpanded(!expanded)} 
      style={{ 
        cursor: "pointer", 
        transition: "all 0.2s ease-in-out",
        border: expanded ? "1px solid var(--primary)" : "1px solid var(--line)"
      }}
    >
      <div className="scoreBlock">
        <span className={`score ${scoreClass}`}>{job.match_score}</span>
        <span>match</span>
      </div>
      <div className="jobMain">
        <div className="jobHeader">
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
              <h2>{job.title}</h2>
              {job.application_priority === "Apply Today" && (
                <span style={{ background: "rgba(16, 185, 129, 0.15)", color: "#10b981", fontSize: "11px", fontWeight: "bold", padding: "2px 6px", borderRadius: "4px" }}>Apply Today</span>
              )}
              {job.application_priority === "Apply This Week" && (
                <span style={{ background: "rgba(59, 130, 246, 0.15)", color: "#3b82f6", fontSize: "11px", fontWeight: "bold", padding: "2px 6px", borderRadius: "4px" }}>Apply This Week</span>
              )}
              {job.is_new && (
                <span style={{ background: "rgba(245, 158, 11, 0.15)", color: "#f59e0b", fontSize: "11px", fontWeight: "bold", padding: "2px 6px", borderRadius: "4px" }}>NEW</span>
              )}
            </div>
            <p>{job.company.name}</p>
          </div>
          <a href={job.url} target="_blank" rel="noreferrer" className="openLink" title="Open internship" onClick={(e) => e.stopPropagation()}>
            <ExternalLink size={18} />
          </a>
        </div>
        <div className="chips">
          <span>{sourcesList.join(", ")}</span>
          <span>{job.remote_status}</span>
          <span>{job.compensation_status}</span>
          {job.location ? <span>{job.location}</span> : null}
          {job.source_count > 1 && <span style={{ color: "var(--primary)" }}>{job.source_count} sources</span>}
          {job.days_since_seen > 0 && <span>Seen {job.days_since_seen}d ago</span>}
        </div>
        <p className="description">{job.description || "No description collected yet."}</p>
        
        {expanded ? (
          <div className="jobDetailsExpanded" style={{ marginTop: "16px", paddingTop: "16px", borderTop: "1px solid var(--line)" }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
              <div>
                <h4 style={{ fontSize: "14px", fontWeight: "bold", marginBottom: "8px", color: "var(--foreground)" }}>Why this matches Ocean:</h4>
                <ul style={{ listStyleType: "disc", paddingLeft: "20px", color: "var(--muted)" }}>
                  {job.match_reasons.map((reason, idx) => (
                    <li key={idx} style={{ fontSize: "13px", marginBottom: "4px" }}>{reason}</li>
                  ))}
                </ul>
              </div>
              <div>
                <div style={{ marginBottom: "12px" }}>
                  <h4 style={{ fontSize: "14px", fontWeight: "bold", marginBottom: "4px", color: "var(--foreground)" }}>Matching Skills:</h4>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {job.matching_skills.length > 0 ? (
                      job.matching_skills.map((skill) => (
                        <span key={skill} style={{ background: "rgba(16, 185, 129, 0.1)", color: "#10b981", padding: "4px 8px", borderRadius: "4px", fontSize: "11px" }}>{skill}</span>
                      ))
                    ) : (
                      <span style={{ fontSize: "12px", color: "var(--muted)" }}>None detected</span>
                    )}
                  </div>
                </div>
                <div>
                  <h4 style={{ fontSize: "14px", fontWeight: "bold", marginBottom: "4px", color: "var(--foreground)" }}>Missing Skills:</h4>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {job.missing_skills.length > 0 ? (
                      job.missing_skills.map((skill) => (
                        <span key={skill} style={{ background: "rgba(239, 68, 68, 0.1)", color: "#ef4444", padding: "4px 8px", borderRadius: "4px", fontSize: "11px" }}>{skill}</span>
                      ))
                    ) : (
                      <span style={{ fontSize: "12px", color: "var(--muted)" }}>None detected</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
            
            <div style={{ display: "flex", gap: "24px", marginTop: "16px", fontSize: "13px", color: "var(--muted)" }}>
              <div><strong>Application Priority:</strong> {job.application_priority}</div>
              <div><strong>Status:</strong> {job.application_status.replace("_", " ")}</div>
              <div><strong>First Seen:</strong> {job.days_since_seen === 0 ? "Today" : `${job.days_since_seen} days ago`}</div>
            </div>
          </div>
        ) : (
          <>
            <div className="skillLine">
              {job.required_skills.slice(0, 6).map((skill) => (
                <span key={skill}>{skill}</span>
              ))}
            </div>
            <div className="reasons">
              {job.match_reasons.slice(0, 3).map((reason) => (
                <span key={reason}>{reason}</span>
              ))}
            </div>
          </>
        )}
      </div>
      <div className="compensationBlock">
        <span>Stipend</span>
        <strong>{job.compensation || "Compensation Not Listed"}</strong>
      </div>
      <div className="trustBlock">
        {job.suspicious ? <AlertTriangle size={18} /> : <ShieldCheck size={18} />}
        <strong>{job.company.trust_score}</strong>
        <span>{job.suspicious ? "review" : "trusted"}</span>
      </div>
    </article>
  );
}

