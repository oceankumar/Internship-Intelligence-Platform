export type Company = {
  id?: string;
  name: string;
  website_url?: string | null;
  linkedin_url?: string | null;
  description?: string | null;
  trust_score: number;
  suspicious: boolean;
  trust_reasons: string[];
  excluded: boolean;
};

export type Job = {
  id?: string;
  company: Company;
  title: string;
  url: string;
  description: string;
  required_skills: string[];
  preferred_skills: string[];
  location?: string | null;
  remote_status: "remote" | "hybrid" | "onsite" | "unknown";
  internship_type: string;
  compensation?: string | null;
  compensation_status: "paid" | "unpaid" | "unknown";
  source: string;
  source_id?: string | null;
  date_posted?: string | null;
  date_discovered: string;
  relevance_score: number;
  score_reasons: string[];
  tags: string[];
  suspicious: boolean;
};

export type DiscoveryResponse = {
  discovered: number;
  stored: number;
  jobs: Job[];
  errors: Record<string, string>;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function fetchJobs(): Promise<Job[]> {
  const response = await fetch(`${API_BASE}/api/jobs`, { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load internships");
  return response.json();
}

export async function runDiscovery(): Promise<DiscoveryResponse> {
  const response = await fetch(`${API_BASE}/api/discovery/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: "frontend react next.js full stack internship paid remote India startup",
      limit_per_source: 20,
      persist: true
    })
  });
  if (!response.ok) throw new Error("Discovery run failed");
  return response.json();
}

export function exportUrl(format: "csv" | "xlsx") {
  return `${API_BASE}/api/export.${format}`;
}

