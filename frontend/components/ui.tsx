import { ReactNode } from "react";
import { SearchX } from "lucide-react";

export function Badge({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
export function Avatar({ name }: { name: string }) {
  return (
    <span className="avatar" aria-hidden="true">
      {name
        .split(/\s+/)
        .map((w) => w[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()}
    </span>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <SearchX size={32} />
      <h3>{title}</h3>
      {children}
    </div>
  );
}
export function Skeleton() {
  return (
    <div aria-label="Loading opportunities" className="skeletons">
      {[1, 2, 3].map((i) => (
        <div className="skeleton" key={i} />
      ))}
    </div>
  );
}
export function Score({ value, label }: { value: number; label: string }) {
  return (
    <span className="score">
      <strong>
        {value}
        <small>/100</small>
      </strong>
      <span>{label}</span>
    </span>
  );
}
export function Breakdown({ data }: { data: Record<string, number> }) {
  return (
    <dl className="breakdown">
      {Object.entries(data).map(([key, value]) => (
        <div key={key}>
          <dt>{key}</dt>
          <dd>
            {value > 0 ? "+" : ""}
            {value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
