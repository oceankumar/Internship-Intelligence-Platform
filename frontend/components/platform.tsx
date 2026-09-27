"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Bookmark,
  BriefcaseBusiness,
  ChartNoAxesCombined,
  Compass,
  Download,
  LayoutDashboard,
  LoaderCircle,
  Radar,
  Search,
  SlidersHorizontal,
  Sparkles,
  UserRound,
  X,
} from "lucide-react";
import {
  Analytics,
  api,
  exportUrl,
  Job,
  label,
  Page,
  Profile,
  Provider,
  Run,
  SavedSearch,
} from "../lib/api";
import { Filters, FilterValues } from "./filters";
import { JobCard, JobDetail } from "./jobs";
import { Insights, Sources } from "./insights";
import { ProfileEditor } from "./profile";
import { Avatar, Badge, Empty, Skeleton } from "./ui";

const navigation = [
  { id: "dashboard", title: "Overview", icon: LayoutDashboard },
  { id: "discover", title: "Discover", icon: Compass },
  { id: "saved", title: "Saved roles", icon: Bookmark },
  { id: "applications", title: "Applications", icon: BriefcaseBusiness },
  { id: "insights", title: "Insights", icon: ChartNoAxesCombined },
  { id: "sources", title: "Sources", icon: Radar },
  { id: "profile", title: "My profile", icon: UserRound },
];
const headings: Record<string, [string, string]> = {
  dashboard: [
    "Your next opportunity",
    "A clearer picture of where to apply next.",
  ],
  discover: ["Internship discovery", "Find the work you want to grow into."],
  saved: ["Your shortlist", "Opportunities worth a closer look."],
  applications: ["Applications", "Keep your next steps in sight."],
  insights: [
    "Career insights",
    "The skills and roles in your opportunity collection.",
  ],
  sources: ["Discovery sources", "Live source health and collection history."],
  profile: ["Candidate profile", "Make your recommendations personal."],
};

export function Platform({ view = "dashboard" }: { view?: string }) {
  const [filters, setFilters] = useState<FilterValues>({});
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("recommended");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page>();
  const [analytics, setAnalytics] = useState<Analytics>();
  const [profile, setProfile] = useState<Profile>();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [selected, setSelected] = useState<Job>();
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [revision, setRevision] = useState(0);
  const [drawer, setDrawer] = useState(false);
  const closeDrawer = useCallback(() => setDrawer(false), []);
  const [searchName, setSearchName] = useState("");
  const searchDialog = useRef<HTMLDialogElement>(null);
  const listing = ["dashboard", "discover", "saved", "applications"].includes(
    view,
  );
  const effective = {
    ...filters,
    ...(view === "saved" ? { favorite: "true" } : {}),
    ...(view === "applications"
      ? {
          applications: "true",
          include_inactive: "true",
          include_hidden: "true",
        }
      : {}),
  };
  const serialized = new URLSearchParams(effective).toString();
  const refresh = useCallback(() => setRevision((n) => n + 1), []);
  const changeFilters = (next: FilterValues) => {
    setFilters(next);
    setQuery(next.q || "");
    setPage(1);
  };

  useEffect(() => {
    const controller = new AbortController();
    api<Analytics>("analytics/market", { signal: controller.signal })
      .then(setAnalytics)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    api<Profile>("profile", { signal: controller.signal })
      .then(setProfile)
      .catch(() => {});
    api<SavedSearch[]>("searches", { signal: controller.signal })
      .then(setSearches)
      .catch(() => {});
    return () => controller.abort();
  }, [revision]);
  useEffect(() => {
    if (!listing) {
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError("");
    const timer = setTimeout(() => {
      api<Page>(
        `internships?${serialized}&page=${page}&limit=12&sort=${sort}`,
        { signal: controller.signal },
      )
        .then(setData)
        .catch((e) => {
          if (e.name !== "AbortError") setError(e.message);
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [serialized, page, sort, revision, listing]);
  useEffect(() => {
    if (view !== "sources") return;
    setLoading(true);
    Promise.all([
      api<Provider[]>("providers/health"),
      api<Run[]>("discovery/runs"),
    ])
      .then(([p, r]) => {
        setProviders(p);
        setRuns(r);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [view, revision]);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const skill = params.get("skill");
    if (skill) setFilters({ skill });
    const job = params.get("job");
    if (job)
      api<Job>("internships/" + encodeURIComponent(job))
        .then(setSelected)
        .catch((e) => setError(e.message));
  }, []);

  async function discover() {
    setRunning(true);
    setError("");
    setNotice("");
    try {
      const result = await api<{
        metrics: {
          fetched: number;
          new: number;
          updated: number;
          provider_failures: number;
        };
        errors: Record<string, string>;
      }>("discovery/run", {
        method: "POST",
        body: JSON.stringify({ limit_per_source: 40, persist: true }),
      });
      setNotice(
        `${result.metrics.fetched} fetched. ${result.metrics.new} new, ${result.metrics.updated} updated. ${result.metrics.provider_failures} source failures.`,
      );
      refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }
  function changed(job: Job) {
    setData(
      (old) =>
        old && {
          ...old,
          items: old.items.map((j) => (j.id === job.id ? job : j)),
        },
    );
    refresh();
  }
  function open(job: Job) {
    setSelected(job);
    const url = new URL(window.location.href);
    url.searchParams.set("job", job.id);
    window.history.replaceState(null, "", url);
  }
  function close() {
    setSelected(undefined);
    const url = new URL(window.location.href);
    url.searchParams.delete("job");
    window.history.replaceState(null, "", url);
  }
  async function saveSearch(e: React.FormEvent) {
    e.preventDefault();
    try {
      setSearches(
        await api<SavedSearch[]>("searches", {
          method: "POST",
          body: JSON.stringify({ name: searchName, filters: effective }),
        }),
      );
      searchDialog.current?.close();
      setSearchName("");
      setNotice("Search saved.");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const title = headings[view] || headings.dashboard;
  return (
    <div className="workspace">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <aside className="sidebar">
        <Link className="brand" href="/">
          <span className="brand-symbol">
            <Compass size={23} />
          </span>
          <span>
            Internship<strong>Intelligence</strong>
          </span>
        </Link>
        <span className="nav-caption">YOUR WORKSPACE</span>
        <nav aria-label="Main navigation">
          {navigation.map(({ id, title, icon: Icon }) => (
            <Link
              key={id}
              href={id === "dashboard" ? "/" : "/" + id}
              className={view === id ? "active" : ""}
              aria-current={view === id ? "page" : undefined}
            >
              <Icon size={18} />
              <span>{title}</span>
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className="local-label">
            <span />
            Private workspace
          </span>
          <Link href="/profile" className="profile-link">
            <Avatar name={profile?.name || "You"} />
            <span>
              {profile?.name || "Your profile"}
              <small>{profile?.skills.length || 0} skills added</small>
            </span>
          </Link>
        </div>
      </aside>
      <main id="main-content">
        <div className="topbar">
          <span>
            Workspace <span className="separator">/</span>{" "}
            {navigation.find((n) => n.id === view)?.title}
          </span>
          <Link href="/profile" aria-label="Open candidate profile">
            <UserRound size={18} />
          </Link>
        </div>
        <div className="page-content">
          <header className="page-heading">
            <div>
              <span className="eyebrow">INTERNSHIP INTELLIGENCE</span>
              <h1>{title[0]}</h1>
              <p>{title[1]}</p>
            </div>
            <div className="header-actions">
              {listing && (
                <details className="export-menu">
                  <summary
                    title="Export filtered internships"
                    aria-label="Export filtered internships"
                  >
                    <Download size={18} />
                  </summary>
                  <div>
                    <a href={exportUrl("csv", effective)}>Download CSV</a>
                    <a href={exportUrl("xlsx", effective)}>Download Excel</a>
                  </div>
                </details>
              )}
              <button
                className="primary-button"
                disabled={running}
                onClick={discover}
              >
                {running ? (
                  <LoaderCircle className="spin" size={17} />
                ) : (
                  <Radar size={17} />
                )}
                <span>{running ? "Discovering..." : "Discover new roles"}</span>
              </button>
            </div>
          </header>
          {error && (
            <div className="error-banner" role="alert">
              <span>{error}</span>
              <button onClick={refresh}>Retry</button>
            </div>
          )}
          {notice && (
            <div className="notice" role="status">
              {notice}
              <button
                className="icon-button"
                aria-label="Dismiss notification"
                onClick={() => setNotice("")}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {view === "dashboard" && (
            <>
              <div className="stats">
                {[
                  ["Active opportunities", analytics?.total],
                  ["New in 24 hours", analytics?.new_today],
                  [
                    "Strong matches",
                    analytics
                      ? analytics.strong_matches + analytics.apply_now
                      : undefined,
                  ],
                  ["Applications", analytics?.applications],
                ].map(([name, value]) => (
                  <div className="stat" key={name}>
                    <span>{name}</span>
                    <strong>{value ?? "--"}</strong>
                  </div>
                ))}
              </div>
              {profile && !profile.skills.length && (
                <div className="profile-nudge">
                  <Sparkles size={20} />
                  <div>
                    <strong>Make these opportunities yours</strong>
                    <p>Add your skills to get a more useful match.</p>
                  </div>
                  <Link href="/profile">
                    Complete profile <ArrowRight size={16} />
                  </Link>
                </div>
              )}
            </>
          )}
          {listing && (
            <>
              <div className="search-toolbar">
                <label className="search-input">
                  <Search size={18} />
                  <input
                    aria-label="Search opportunities"
                    placeholder="Search roles, companies, or paid remote frontend internships"
                    value={query}
                    onChange={(e) => {
                      setQuery(e.target.value);
                      setFilters({ ...filters, q: e.target.value });
                      setPage(1);
                    }}
                  />
                  {query && (
                    <button
                      className="icon-button"
                      aria-label="Clear search"
                      onClick={() => changeFilters({ ...filters, q: "" })}
                    >
                      <X size={16} />
                    </button>
                  )}
                </label>
                <button
                  className="filter-toggle"
                  onClick={() => setDrawer(!drawer)}
                  aria-expanded={drawer}
                >
                  <SlidersHorizontal size={17} />
                  Filters
                </button>
                <label className="sort-label">
                  <span className="sr-only">Sort opportunities</span>
                  <select
                    value={sort}
                    onChange={(e) => {
                      setSort(e.target.value);
                      setPage(1);
                    }}
                  >
                    {[
                      ["recommended", "Recommended"],
                      ["newest", "Newest"],
                      ["match", "Highest match"],
                      ["opportunity", "Highest opportunity"],
                      ["trust", "Highest trust"],
                      ["deadline", "Closing soon"],
                      ["stipend", "Highest stipend"],
                    ].map(([v, t]) => (
                      <option value={v} key={v}>
                        {t}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              {view !== "applications" && (
                <div className="quick-tabs" aria-label="Quick filters">
                  {[
                    ["All", {}],
                    ["Recommended", { recommended: "true" }],
                    ["New", { posted_days: "1" }],
                    ["Remote", { remote: "remote" }],
                    ["Paid", { paid: "true" }],
                    ["Closing soon", { closing_days: "7" }],
                  ].map(([name, preset]) => (
                    <button
                      key={String(name)}
                      className={
                        JSON.stringify(filters) === JSON.stringify(preset)
                          ? "active"
                          : ""
                      }
                      onClick={() => changeFilters(preset as FilterValues)}
                    >
                      {String(name)}
                    </button>
                  ))}
                </div>
              )}
              <div
                className={
                  "discovery-layout " +
                  (view === "discover" ? "with-filters" : "")
                }
              >
                {(view === "discover" || drawer) && (
                  <Filters
                    value={filters}
                    onChange={changeFilters}
                    open={drawer}
                    onClose={closeDrawer}
                    searches={searches}
                    onSave={() => searchDialog.current?.showModal()}
                  />
                )}
                <section className="results" aria-label="Internship results">
                  <div className="results-heading">
                    <h2>
                      {view === "dashboard"
                        ? "Opportunities for you"
                        : view === "applications"
                          ? "Your pipeline"
                          : "Opportunities"}
                    </h2>
                    <span>{data?.total ?? 0} results</span>
                  </div>
                  {data?.parsed_filters &&
                    Object.keys(data.parsed_filters).length > 0 && (
                      <div className="badges parsed-filters">
                        {Object.entries(data.parsed_filters).map(([k, v]) => (
                          <Badge key={k}>
                            {label(k)}: {String(v)}
                          </Badge>
                        ))}
                      </div>
                    )}
                  {loading ? (
                    <Skeleton />
                  ) : data?.items.length ? (
                    view === "applications" ? (
                      <div className="application-list">
                        {data.items.map((j) => (
                          <article key={j.id} className="application-row">
                            <Avatar name={j.company.name} />
                            <div>
                              <button
                                className="title-button"
                                onClick={() => open(j)}
                              >
                                {j.title}
                              </button>
                              <p>{j.company.name}</p>
                            </div>
                            <Badge>{label(j.application_status)}</Badge>
                            <span>
                              {j.applied_at
                                ? new Date(j.applied_at).toLocaleDateString()
                                : "Not applied yet"}
                            </span>
                            <button onClick={() => open(j)}>Update</button>
                          </article>
                        ))}
                      </div>
                    ) : (
                      <div className="job-grid">
                        {data.items.map((j) => (
                          <JobCard
                            key={j.id}
                            job={j}
                            onOpen={() => open(j)}
                            onChange={changed}
                          />
                        ))}
                      </div>
                    )
                  ) : (
                    <Empty
                      title={
                        view === "applications"
                          ? "No applications yet"
                          : view === "saved"
                            ? "Your shortlist is empty"
                            : "No internships match these filters"
                      }
                    >
                      <p>
                        {view === "applications"
                          ? "Find a role and mark your application status."
                          : "Try a broader search or discover new opportunities."}
                      </p>
                      <button onClick={() => changeFilters({})}>
                        Clear filters
                      </button>
                    </Empty>
                  )}
                  {data && data.total > data.limit && (
                    <div className="pagination">
                      <span>
                        Page {page} of {Math.ceil(data.total / data.limit)}
                      </span>
                      <button
                        className="icon-button"
                        aria-label="Previous page"
                        disabled={page === 1}
                        onClick={() => setPage(page - 1)}
                      >
                        <ArrowLeft size={18} />
                      </button>
                      <button
                        className="icon-button"
                        aria-label="Next page"
                        disabled={page * data.limit >= data.total}
                        onClick={() => setPage(page + 1)}
                      >
                        <ArrowRight size={18} />
                      </button>
                    </div>
                  )}
                </section>
              </div>
            </>
          )}
          {view === "profile" && <ProfileEditor onSaved={refresh} />}
          {view === "insights" &&
            (analytics ? (
              <Insights
                data={analytics}
                onSkill={(s) => {
                  window.location.href =
                    "/discover?skill=" + encodeURIComponent(s);
                }}
              />
            ) : (
              <Skeleton />
            ))}
          {view === "sources" &&
            (loading ? (
              <Skeleton />
            ) : (
              <Sources providers={providers} runs={runs} />
            ))}
        </div>
        <footer className="page-footer">
          Source-backed opportunities. Your decision, always.
        </footer>
      </main>
      {selected && (
        <JobDetail
          key={selected.id}
          job={selected}
          onClose={close}
          onChange={changed}
        />
      )}
      <dialog ref={searchDialog} className="small-dialog">
        <form onSubmit={saveSearch}>
          <div className="section-heading">
            <h2>Save this search</h2>
            <button
              type="button"
              className="icon-button"
              aria-label="Close save search"
              onClick={() => searchDialog.current?.close()}
            >
              <X size={18} />
            </button>
          </div>
          <label>
            Search name
            <input
              required
              maxLength={80}
              value={searchName}
              onChange={(e) => setSearchName(e.target.value)}
            />
          </label>
          <button className="primary-button">Save search</button>
        </form>
      </dialog>
    </div>
  );
}
