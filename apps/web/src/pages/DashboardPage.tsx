import { useQuery } from "@tanstack/react-query";

import { ErrorState, LoadingState, MetricGrid, PageHeader, Panel, formatMoney, formatNumber, formatPercent, titleCase } from "../components/Workspace";
import { useAuth } from "../features/auth/AuthProvider";
import { getDashboard } from "../features/operations/api";
import type { DashboardMetric } from "../features/operations/types";

function showMetric(metric: DashboardMetric) {
  if (typeof metric.value !== "number") return metric.value;
  if (metric.format === "currency") return formatMoney(metric.value);
  if (metric.format === "percent") return formatPercent(metric.value);
  return formatNumber(metric.value);
}

function inferredMetrics(data: Record<string, unknown>): DashboardMetric[] {
  return Object.entries(data)
    .filter(([, value]) => typeof value === "number" || typeof value === "string")
    .slice(0, 12)
    .map(([key, value]) => ({
      label: titleCase(key), value: value as number | string,
      format: key.endsWith("_cents") ? "currency" : key.endsWith("_rate") || key.endsWith("_bps") ? "percent" : "number",
    }));
}

function dashboardMetrics(data: Record<string, unknown>): DashboardMetric[] {
  if (Array.isArray(data.metrics)) return data.metrics as DashboardMetric[];
  const sections = [data.today, data.sales, data.finance, data.tasks].filter((value): value is Record<string, unknown> => Boolean(value) && typeof value === "object" && !Array.isArray(value));
  const flat = Object.assign({}, ...sections);
  return inferredMetrics(flat).map((metric) => {
    const label = metric.label.toLowerCase();
    return { ...metric, format: label.includes("cents") || label.includes("pipeline") || label.includes("mrr") || label.includes("revenue") || label.includes("cash") || label.includes("burn") ? "currency" : label.includes("rate") ? "percent" : metric.format };
  });
}

export function DashboardPage() {
  const { user } = useAuth();
  const query = useQuery({ queryKey: ["dashboard"], queryFn: getDashboard });
  const role = user?.roles.includes("ceo") || user?.roles.includes("admin") ? "Leadership" : user?.department === "sales" ? "Sales" : "Product";
  const metrics = dashboardMetrics(query.data ?? {});

  return <div className="workspace-page">
    <PageHeader eyebrow={`${role} cockpit`} title={`Good ${new Date().getHours() < 13 ? "morning" : "afternoon"}, ${user?.display_name.split(" ")[0] ?? "team"}.`} description="A live view of what needs attention across SIFT today." />
    {query.isLoading && <LoadingState label="Loading your dashboard" />}
    {query.isError && <ErrorState error={query.error} retry={() => void query.refetch()} />}
    {query.data && <>
      {metrics.length > 0 ? <MetricGrid items={metrics.map((metric) => ({ label: metric.label, value: showMetric(metric), detail: metric.delta === undefined ? undefined : `${metric.delta >= 0 ? "+" : ""}${metric.delta}% vs previous period`, tone: metric.delta === undefined ? undefined : metric.delta >= 0 ? "good" : "warn" }))} /> : <Panel><p className="quiet-copy">No business indicators have been recorded for this period yet.</p></Panel>}
      {query.data.pipeline?.stages && <Panel title="Pipeline movement" subtitle="Current opportunity value by stage"><div className="funnel-bars">{query.data.pipeline.stages.map((stage) => <div key={stage.stage}><span>{titleCase(stage.stage)}</span><div><i style={{ width: `${Math.max(3, Math.min(100, stage.count * 9))}%` }} /></div><strong>{stage.count} · {formatMoney(stage.value_cents)}</strong></div>)}</div></Panel>}
      {query.data.products && <Panel title="Product pulse" subtitle="ARGUS and LYNX runtime health"><div className="product-strip">{query.data.products.map((product) => <article key={product.id}><span className={`health-dot ${product.status}`} /> <strong>{product.name}</strong><span>{titleCase(product.status)}</span><small>{formatNumber(product.runs_today)} runs today</small></article>)}</div></Panel>}
    </>}
  </div>;
}
