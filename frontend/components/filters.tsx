"use client";
import { label, roles, SavedSearch, statuses } from "../lib/api";
import { useEffect, useRef } from "react";
import { X, Trash2 } from "lucide-react";
export type FilterValues = Record<string, string>;
export function Filters({
  value,
  onChange,
  open,
  onClose,
  searches,
  onSave,
  onDelete,
  compareStipends = false,
  readOnly = false,
}: {
  value: FilterValues;
  onChange: (v: FilterValues) => void;
  open: boolean;
  onClose: () => void;
  searches: SavedSearch[];
  onSave: () => void;
  onDelete: (name: string) => void;
  compareStipends?: boolean;
  readOnly?: boolean;
}) {
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!open || !window.matchMedia("(max-width:850px)").matches) return;
    const previous = document.activeElement as HTMLElement;
    const element = panel.current!;
    element.querySelector<HTMLButtonElement>("button")?.focus();
    function keyboard(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
      if (e.key !== "Tab") return;
      const items = [
        ...element.querySelectorAll<HTMLElement>("button,input,select,summary"),
      ].filter((el) => el.offsetParent !== null);
      const first = items[0],
        last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      }
      if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
    element.addEventListener("keydown", keyboard);
    return () => {
      element.removeEventListener("keydown", keyboard);
      previous?.focus();
    };
  }, [open, onClose]);
  function set(k: string, v: string) {
    const next = { ...value };
    if (v) next[k] = v;
    else delete next[k];
    onChange(next);
  }
  return (
    <aside
      ref={panel}
      className={"filter-panel " + (open ? "mobile-open" : "")}
      aria-label="Opportunity filters"
    >
      <div className="section-heading">
        <h3>Refine your search</h3>
        <button
          className="icon-button mobile-only"
          aria-label="Close filters"
          onClick={onClose}
        >
          <X size={18} />
        </button>
      </div>
      <label>
        Role
        <select
          aria-label="Role"
          value={value.role || ""}
          onChange={(e) => set("role", e.target.value)}
        >
          <option value="">All roles</option>
          {roles.map((r) => (
            <option key={r}>{r}</option>
          ))}
        </select>
      </label>
      <label>
        Workplace
        <select
          value={value.remote || ""}
          onChange={(e) => set("remote", e.target.value)}
        >
          <option value="">Any workplace</option>
          {["remote", "hybrid", "onsite"].map((r) => (
            <option key={r}>{r}</option>
          ))}
        </select>
      </label>
      <label>
        Skills
        <input
          value={value.skill || ""}
          placeholder="react, typescript"
          onChange={(e) => set("skill", e.target.value)}
        />
      </label>
      <label>
        Country
        <input
          value={value.country || ""}
          placeholder="Any country"
          onChange={(e) => set("country", e.target.value)}
        />
      </label>
      <label>
        Company
        <input
          value={value.company || ""}
          placeholder="Any company"
          onChange={(e) => set("company", e.target.value)}
        />
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={value.paid === "true"}
          onChange={(e) => set("paid", e.target.checked ? "true" : "")}
        />
        Confirmed paid only
      </label>
      <label>
        Minimum match <span>{value.min_match || 0}</span>
        <input
          type="range"
          min="0"
          max="100"
          step="5"
          value={value.min_match || 0}
          onChange={(e) => set("min_match", e.target.value)}
        />
      </label>
      <label>
        Posted within
        <select
          value={value.posted_days || ""}
          onChange={(e) => set("posted_days", e.target.value)}
        >
          <option value="">Any time</option>
          <option value="1">24 hours</option>
          <option value="7">7 days</option>
          <option value="30">30 days</option>
        </select>
      </label>
      <details open={compareStipends ? true : undefined}>
        <summary>More filters</summary>
        <label>
          Application status
          <select
            value={value.status || ""}
            onChange={(e) => set("status", e.target.value)}
          >
            <option value="">Any status</option>
            {statuses.map((s) => (
              <option key={s} value={s}>
                {label(s)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Source
          <select
            value={value.source || ""}
            onChange={(e) => set("source", e.target.value)}
          >
            <option value="">All sources</option>
            {[
              "yc_jobs",
              "remoteok",
              "simplify_jobs",
              "github_jobs",
              "startup_career_pages",
              "public_datasets",
            ].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          Minimum trust
          <input
            type="number"
            min="0"
            max="100"
            value={value.min_trust || ""}
            onChange={(e) => set("min_trust", e.target.value)}
          />
        </label>
        <label>
          Minimum opportunity
          <input
            type="number"
            min="0"
            max="100"
            value={value.min_opportunity || ""}
            onChange={(e) => set("min_opportunity", e.target.value)}
          />
        </label>
        <label>
          Max experience (months)
          <input
            type="number"
            min="0"
            max="600"
            value={value.max_experience || ""}
            onChange={(e) => set("max_experience", e.target.value)}
          />
        </label>
        <label>
          Closing within (days)
          <input
            type="number"
            min="1"
            max="365"
            value={value.closing_days || ""}
            onChange={(e) => set("closing_days", e.target.value)}
          />
        </label>
        <label>
          Currency
          <select
            value={value.currency || ""}
            aria-label="Currency"
            onChange={(e) => set("currency", e.target.value)}
          >
            <option value="">Any</option>
            {["INR", "USD", "EUR", "GBP"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          Pay period
          <select
            value={value.period || ""}
            aria-label="Pay period"
            onChange={(e) => set("period", e.target.value)}
          >
            <option value="">Any</option>
            {["hour", "month", "year"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          Minimum stipend
          <input
            type="number"
            min="0"
            value={value.min_stipend || ""}
            onChange={(e) => set("min_stipend", e.target.value)}
          />
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={value.include_inactive === "true"}
            onChange={(e) =>
              set("include_inactive", e.target.checked ? "true" : "")
            }
          />
          Include inactive
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={value.include_hidden === "true"}
            onChange={(e) =>
              set("include_hidden", e.target.checked ? "true" : "")
            }
          />
          Include hidden
        </label>
      </details>
      <label className="check"><input type="checkbox" checked={value.include_programs === "true"} onChange={(e) => onChange({...value, include_programs: e.target.checked ? "true" : "", include_inactive: e.target.checked ? "true" : ""})} />Include program catalogs</label>
      <div className="filter-actions">
        <button onClick={() => onChange({})}>Clear filters</button>
        <button disabled={readOnly} title={readOnly ? "Public demo is read-only" : undefined} onClick={onSave}>Save search</button>
      </div>
      {searches.length > 0 && (
        <label>
          Saved searches
          <select
            value=""
            onChange={(e) => {
              const s = searches.find((s) => s.name === e.target.value);
              if (s) onChange(s.filters);
            }}
          >
            <option value="">Choose a search</option>
            {searches.map((s) => (
              <option key={s.name}>{s.name}</option>
            ))}
          </select>
        </label>
      )}
      {searches.map((s) => <div className="section-heading" key={s.name}><span>{s.name}</span><button className="icon-button" aria-label={"Delete search " + s.name} title={"Delete search " + s.name} onClick={() => onDelete(s.name)}><Trash2 size={16}/></button></div>)}
    </aside>
  );
}
