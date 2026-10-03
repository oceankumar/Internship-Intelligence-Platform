"use client";
import {
  Bookmark,
  ExternalLink,
  EyeOff,
  MapPin,
  X,
  Check,
  ShieldCheck,
  RotateCcw,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, Job, label, patchJob, publicLink, statuses } from "../lib/api";
import { Avatar, Badge, Breakdown, Score } from "./ui";

export function JobCard({
  job,
  onOpen,
  onChange,
}: {
  job: Job;
  onOpen: () => void;
  onChange: (j: Job) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save() {
    setBusy(true);
    try {
      onChange(await patchJob(job.id, { favorite: !job.favorite }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <article className="job-card">
      <div className="card-top">
        <Avatar name={job.company.name} />
        <div className="company-line">
          <span>{job.company.name}</span>
          <small>
            {job.date_posted
              ? "Posted " + new Date(job.date_posted).toLocaleDateString()
              : "Posting date unavailable"}
          </small>
        </div>
        <button
          className={"icon-button " + (job.favorite ? "selected" : "")}
          title={job.favorite ? "Unsave role" : "Save role"}
          aria-label={job.favorite ? "Unsave role" : "Save role"}
          aria-pressed={job.favorite}
          disabled={busy}
          onClick={save}
        >
          <Bookmark size={18} fill={job.favorite ? "currentColor" : "none"} />
        </button>
      </div>
      <button className="title-button" onClick={onOpen}>
        {job.title}
      </button>
      {job.provenance.sample === true && (
        <Badge tone="amber">Sample record</Badge>
      )}
      {job.provenance.listing_kind === "program_catalog" && (
        <Badge tone="amber">Program catalog · Opening unverified</Badge>
      )}
      <div className="location">
        <MapPin size={14} />
        {job.location || "Location not listed"}
      </div>
      <div className="badges">
        <Badge>{label(job.remote_status)}</Badge>
        <Badge tone={job.compensation_status === "paid" ? "green" : ""}>
          {job.compensation || label(job.compensation_status) + " compensation"}
        </Badge>
        {job.stale && <Badge tone="amber">Possibly stale</Badge>}
      </div>
      <p className="card-summary">
        {job.summary ||
          "Open the source listing to confirm responsibilities and requirements."}
      </p>
      <div className="skills">
        {job.matching_skills.slice(0, 4).map((s) => (
          <Badge key={s} tone="green">
            {s}
          </Badge>
        ))}
        {job.missing_skills.length > 0 && (
          <small>{job.missing_skills.length} skill gaps</small>
        )}
      </div>
      <div className="card-bottom">
        <button
          className="score-button"
          onClick={onOpen}
          title="View score explanation"
        >
          <Score value={job.opportunity_score} label="Opportunity" />
          <Score value={job.match_score} label="Match" />
        </button>
        <span className="trust-label">
          <ShieldCheck size={14} />
          {job.trust_score} listing trust
        </span>
      </div>
      <div className="card-footer">
        <Badge tone={job.application_priority === "Apply Now" ? "green" : ""}>
          {job.application_priority}
        </Badge>
        <button className="text-button" onClick={onOpen}>
          View details <span aria-hidden="true">→</span>
        </button>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </article>
  );
}

export function JobDetail({
  job: initial,
  onClose,
  onChange,
}: {
  job: Job;
  onClose: () => void;
  onChange: (j: Job) => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [job, setJob] = useState(initial);
  const [error, setError] = useState("");
  const [notes, setNotes] = useState(job.notes);
  const [contact, setContact] = useState(job.contact);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const dialog = ref.current!;
    dialog.showModal();
    return () => dialog.close();
  }, []);
  const sourceValues = job.provenance.source_values as Record<string, unknown> | undefined;
  async function update(changes: Partial<Job>) {
    setBusy(true);
    setError("");
    try {
      const next = await patchJob(job.id, changes);
      setJob(next);
      onChange(next);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function correct(field: string, value: string | boolean) {
    try {
      const next = await api<Job>("internships/" + job.id + "/corrections", {
        method: "PATCH",
        body: JSON.stringify({ [field]: value }),
      });
      setJob(next);
      onChange(next);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <dialog
      ref={ref}
      className="detail-dialog"
      onCancel={onClose}
      aria-labelledby="detail-title"
    >
      <div className="detail-toolbar">
        <span>Opportunity details</span>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Close details"
        >
          <X size={20} />
        </button>
      </div>
      <div className="detail-content">
        <div className="card-top">
          <Avatar name={job.company.name} />
          <div>
            <span>{job.company.name}</span>
            <p className="muted">{job.location || "Location not listed"}</p>
          </div>
        </div>
        <h2 id="detail-title">{job.title}</h2>
        <div className="badges">
          <Badge>{label(job.remote_status)}</Badge>
          <Badge>{job.compensation || "Compensation not listed"}</Badge>
          <Badge>{job.application_priority}</Badge>
        </div>
        <div className="detail-scores">
          <Score value={job.opportunity_score} label="Opportunity" />
          <Score value={job.match_score} label="Match" />
          <Score value={job.eligibility_score} label="Eligibility" />
          <Score value={job.trust_score} label="Listing trust" />
          <Score value={job.evidence_confidence} label="Evidence" />
        </div>
        <div className="detail-actions">
          <a
            className="primary-button"
            href={publicLink(job.url)}
            target="_blank"
            rel="noreferrer"
          >
            Apply on source <ExternalLink size={16} />
          </a>
          <button
            disabled={busy}
            onClick={() => update({ application_status: "applied" })}
          >
            <Check size={16} />
            Mark applied
          </button>
          <button
            className="icon-button"
            aria-label="Save internship"
            onClick={() => update({ favorite: !job.favorite })}
          >
            <Bookmark size={18} fill={job.favorite ? "currentColor" : "none"} />
          </button>
          <button
            className="icon-button"
            aria-label={job.hidden ? "Unhide internship" : "Hide internship"}
            onClick={() => update({ hidden: !job.hidden })}
          >
            <EyeOff size={18} />
          </button>
        </div>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <section>
          <h3>Why this opportunity?</h3>
          <Breakdown data={job.score_breakdown} />
          <p className="muted">
            Freshness uses the posting date when available. An unknown posting
            date receives less weight.
          </p>
        </section>
        <section>
          <h3>Why this match?</h3>
          <p>Fit: {job.fit_score === null ? "Unknown requirements" : job.fit_score + "/100"}. Evidence completeness: {job.evidence_confidence}/100.</p>
          <div className="badges">{Object.entries(job.preference_compliance || {}).map(([key,value]) => <Badge key={key} tone={value === "matches" ? "green" : "amber"}>{label(key)}: {value}</Badge>)}</div>
          <Breakdown data={job.match_breakdown} />
          <ul>
            {job.match_reasons
              .filter((r) => !r.includes("points"))
              .map((r, i) => (
                <li key={i}>{r}</li>
              ))}
          </ul>
          <h4>Missing required skills</h4>
          <div className="badges">
            {job.missing_skills.length ? (
              job.missing_skills.map((s) => (
                <Badge key={s} tone="amber">
                  {s}
                </Badge>
              ))
            ) : (
              <span className="muted">
                No gaps detected in the stated skills.
              </span>
            )}
          </div>
        </section>
        <section>
          <h3>{job.eligibility_status}</h3>
          <ul>
            {job.eligibility_reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>
        <section>
          <h3>Trust evidence</h3>
          <p>Listing risk: {job.risk_state}. Company identity evidence: {job.company.trust_score}/100.</p>
          <ul>{job.risk_reasons?.map((r) => <li key={r}>{r}</li>)}</ul>
          <ul>
            {job.company.trust_reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>
        <section>
          <h3>Role description</h3>
          <p className="full-description">
            {job.description || "Description not provided by the source."}
          </p>
          <h4>Required skills</h4>
          <div className="badges">
            {job.required_skills.map((s) => (
              <Badge key={s}>{s}</Badge>
            ))}
          </div>
          {job.preferred_skills.length > 0 && (
            <>
              <h4>Preferred skills</h4>
              <div className="badges">
                {job.preferred_skills.map((s) => (
                  <Badge key={s}>{s}</Badge>
                ))}
              </div>
            </>
          )}
        </section>
        <section>
          <h3>Source verification</h3>
          <p>
            Found through {job.sources.length} source
            {job.sources.length === 1 ? "" : "s"}:{" "}
            {job.sources.map(label).join(", ")}
          </p>
          {job.original_urls.filter(publicLink).map((url) => (
            <a
              className="source-link"
              key={url}
              href={url}
              target="_blank"
              rel="noreferrer"
            >
              {url}
              <ExternalLink size={12} />
            </a>
          ))}
          <p className="muted">
            Deadline:{" "}
            {job.deadline
              ? new Date(job.deadline).toLocaleDateString()
              : "Not listed"}
          </p>
        </section>
        <section>
          <h3>Application tracker</h3>
          <label>
            Status
            <select
              value={job.application_status}
              disabled={busy}
              onChange={(e) => update({ application_status: e.target.value })}
            >
              {statuses.map((s) => (
                <option key={s} value={s}>
                  {label(s)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Notes
            <textarea
              aria-label="Notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              maxLength={5000}
            />
          </label>
          <label>
            Contact
            <input
              value={contact}
              onChange={(e) => setContact(e.target.value)}
              maxLength={300}
            />
          </label>
          <div className="form-grid">
            {(["interview_at", "reminder_at"] as const).map((field) => (
              <label key={field}>
                {field === "interview_at" ? "Interview date" : "Reminder date"}
                <input
                  type="date"
                  value={job[field]?.slice(0, 10) || ""}
                  onChange={(e) =>
                    update({
                      [field]: e.target.value
                        ? e.target.value + "T00:00:00Z"
                        : null,
                    })
                  }
                />
              </label>
            ))}
          </div>
          <button disabled={busy} onClick={() => update({ notes, contact })}>
            Save notes
          </button>
        </section>
        <details>
          <summary>Correct extracted information</summary>
          {Object.keys(job.corrections || {}).length > 0 && <button onClick={() => correct("reset",true)}><RotateCcw size={16}/>Reset to source value</button>}
          <p className="muted">{Object.keys(job.corrections || {}).length ? "User override is active" : "Source extraction; no user override"}</p>
          {sourceValues && <p className="muted">Source extraction: {String(sourceValues.remote_status || "unknown")} workplace; {String(sourceValues.compensation_status || "unknown")} compensation. Current values are shown below.</p>}
          <div className="form-grid">
            <label>
              Remote status
              <select
                value={job.remote_status}
                onChange={(e) => correct("remote_status", e.target.value)}
              >
                {["remote", "hybrid", "onsite", "unknown"].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
            <label>
              Compensation
              <select
                value={job.compensation_status}
                onChange={(e) => correct("compensation_status", e.target.value)}
              >
                {["paid", "unpaid", "unknown"].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
          </div>
        </details>
      </div>
    </dialog>
  );
}
