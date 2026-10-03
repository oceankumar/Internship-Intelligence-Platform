import { Analytics, label, Provider, Run } from "../lib/api";
import { Badge, Empty } from "./ui";

export function Bars({
  title,
  values,
  onClick,
}: {
  title: string;
  values: Record<string, number>;
  onClick?: (s: string) => void;
}) {
  const max = Math.max(1, ...Object.values(values));
  return (
    <section className="chart">
      <h3>{title}</h3>
      {Object.keys(values).length ? (
        Object.entries(values).map(([name, count]) => (
          <div className="bar-row" key={name}>
            <div>
              <button disabled={!onClick} onClick={() => onClick?.(name)}>
                {label(name)}
              </button>
              <strong>{count}</strong>
            </div>
            <span className="bar-track">
              <span style={{ width: (count / max) * 100 + "%" }} />
            </span>
          </div>
        ))
      ) : (
        <p className="muted">No data yet</p>
      )}
    </section>
  );
}
export function Insights({
  data,
  onSkill,
}: {
  data: Analytics;
  onSkill: (s: string) => void;
}) {
  if (!data.total)
    return (
      <Empty title="No market insights yet">
        <p>Discover opportunities to build your market picture.</p>
      </Empty>
    );
  return (
    <>
      <p className="muted">
        Based on {data.total} visible, active listings in your collection.
      </p>
      <div className="charts">
        <Bars
          title="Your skill gaps in relevant roles"
          values={data.missing_skills}
          onClick={onSkill}
        />
        <Bars
          title="Most requested skills"
          values={data.skills}
          onClick={onSkill}
        />
        <Bars title="Role families" values={data.roles} />
        <Bars title="Application pipeline" values={data.pipeline} />
        <Bars title="Workplace" values={data.remote} />
        <Bars title="Compensation evidence" values={data.paid} />
        <Bars title="Opportunity priorities" values={data.priorities} />
        <Bars title="Top companies" values={data.companies} />
      </div>
    </>
  );
}
export function Sources({
  providers,
  runs,
}: {
  providers: Provider[];
  runs: Run[];
}) {
  return (
    <>
      <div className="provider-list">
        {providers.map((p) => (
          <article className="provider-row" key={p.source}>
            <div>
              <h3>{label(p.source)}</h3>
              <p className="muted">
                {p.last_success
                  ? "Last successful run: " +
                    new Date(p.last_success).toLocaleString()
                  : "No successful run recorded"}
              </p>
              {p.error && <p>{p.error}</p>}
              {p.warnings?.map((w, i) => (
                <small key={i}>{w}</small>
              ))}
            </div>
            <div>
              <Badge
                tone={
                  p.status === "healthy"
                    ? "green"
                    : p.status === "failing"
                      ? "amber"
                      : ""
                }
              >
                {label(p.status)}
              </Badge>
              <p>
                {p.raw_jobs ?? 0} fetched · {p.internships ?? 0} accepted
              </p>
              <p>{p.active_records ?? 0} active · {p.useful_records ?? 0} with substantial description</p>
              <small>{p.last_useful_result ? "Last substantial result: " + new Date(p.last_useful_result).toLocaleString() : "No substantial result recorded"}</small>
              <small>
                {p.duration_ms ? (p.duration_ms / 1000).toFixed(1) + "s" : ""}
              </small>
            </div>
          </article>
        ))}
      </div>
      <h2 className="subheading">Discovery history</h2>
      {runs.length ? (
        runs.slice(0, 20).map((r) => (
          <details className="run" key={r.id}>
            <summary>
              {new Date(r.started_at).toLocaleString()}{" "}
              <Badge>{r.status}</Badge>
            </summary>
            <dl className="breakdown">
              {Object.entries(r.metrics || {})
                .filter(([, v]) => typeof v === "number")
                .map(([k, v]) => (
                  <div key={k}>
                    <dt>{label(k)}</dt>
                    <dd>{String(v)}</dd>
                  </div>
                ))}
            </dl>
            {Object.entries(r.errors || {}).map(([k, v]) => (
              <p key={k}>
                {label(k)}: {v}
              </p>
            ))}
          </details>
        ))
      ) : (
        <Empty title="No discovery runs yet" />
      )}
    </>
  );
}
