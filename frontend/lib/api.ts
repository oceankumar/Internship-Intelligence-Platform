export type Profile = {
  name: string;
  skills: string[];
  preferred_roles: string[];
  experience_months: number;
  education: string;
  graduation_year: number | null;
  country: string;
  preferred_locations: string[];
  remote_preference: boolean;
  paid_only: boolean;
};
export type Job = {
  id: string;
  title: string;
  url: string;
  description: string;
  summary: string;
  role_family: string;
  company: {
    name: string;
    website_url: string | null;
    trust_score: number;
    trust_reasons: string[];
    excluded: boolean;
  };
  location: string | null;
  country: string | null;
  remote_status: string;
  compensation: string | null;
  compensation_status: string;
  match_score: number;
  opportunity_score: number;
  eligibility_score: number;
  eligibility_status: string;
  eligibility_reasons: string[];
  match_reasons: string[];
  match_breakdown: Record<string, number>;
  score_breakdown: Record<string, number>;
  trust_level: string;
  required_skills: string[];
  preferred_skills: string[];
  matching_skills: string[];
  missing_skills: string[];
  source: string;
  sources: string[];
  source_count: number;
  original_urls: string[];
  date_posted: string | null;
  date_discovered: string;
  deadline: string | null;
  favorite: boolean;
  hidden: boolean;
  active: boolean;
  stale: boolean;
  is_new: boolean;
  application_priority: string;
  application_status: string;
  applied_at: string | null;
  notes: string;
  contact: string;
  interview_at: string | null;
  reminder_at: string | null;
  provenance: Record<string, unknown>;
};
export type Page = {
  items: Job[];
  total: number;
  page: number;
  limit: number;
  parsed_filters: Record<string, string | boolean>;
};
export type Analytics = {
  total: number;
  new_today: number;
  apply_now: number;
  strong_matches: number;
  closing_soon: number;
  applications: number;
  roles: Record<string, number>;
  skills: Record<string, number>;
  missing_skills: Record<string, number>;
  remote: Record<string, number>;
  paid: Record<string, number>;
  pipeline: Record<string, number>;
  discovered: Record<string, number>;
  companies: Record<string, number>;
  priorities: Record<string, number>;
};
export type Provider = {
  source: string;
  status: string;
  raw_jobs?: number;
  internships?: number;
  rejected?: number;
  duration_ms?: number;
  error?: string;
  warnings?: string[];
  last_success?: string;
};
export type Run = {
  id: string;
  started_at: string;
  status: string;
  metrics?: Record<string, unknown>;
  errors?: Record<string, string>;
};
export type SavedSearch = { name: string; filters: Record<string, string> };
export const statuses = [
  "not_applied",
  "planning",
  "applied",
  "assessment",
  "interview",
  "offer",
  "rejected",
  "withdrawn",
];
export const roles = [
  "frontend",
  "full-stack",
  "backend",
  "software engineering",
  "AI/ML",
  "data science",
  "data engineering",
  "product",
  "design",
  "DevOps",
  "cybersecurity",
  "research",
];
export const label = (s: string) =>
  s.replaceAll("_", " ").replace(/^\w/, (c) => c.toUpperCase());
export function publicLink(value: string) {
  try {
    const u = new URL(value);
    return ["http:", "https:"].includes(u.protocol) &&
      !u.username &&
      !u.password
      ? u.href
      : undefined;
  } catch {
    return undefined;
  }
}
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch("/api/" + path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(
      data.error?.message ||
        (typeof data.detail === "string"
          ? data.detail
          : "Request failed. Please retry."),
    );
  }
  return response.json();
}
export const patchJob = (id: string, changes: Partial<Job>) =>
  api<Job>("applications/" + id, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
export function exportUrl(format: string, filters: Record<string, string>) {
  return "/api/export." + format + "?" + new URLSearchParams(filters);
}
