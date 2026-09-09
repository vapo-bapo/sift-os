import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import type { CSSProperties } from "react";

import { Badge, EmptyState, ErrorState, LoadingState, MetricGrid, PageHeader, Panel, formatMoney, formatNumber, formatPercent } from "../components/Workspace";
import { getProductMetrics, itemsOf } from "../features/operations/api";
import type { ProductSummary } from "../features/operations/types";

export function ProductOperationsPage() {
  const query = useQuery({ queryKey: ["products", "metrics"], queryFn: getProductMetrics, refetchInterval: 60_000 });
  const products = itemsOf(query.data);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = products.find((product) => product.id === selectedId) ?? products[0];
  return <div className="workspace-page">
    <PageHeader eyebrow="Runtime intelligence" title="Product Operations" description="Health, usage, reliability and unit economics from authenticated product events." />
    {query.isLoading && <LoadingState label="Loading product telemetry" />}
    {query.isError && <ErrorState error={query.error} retry={() => void query.refetch()} />}
    {query.data && !products.length && <EmptyState title="No product telemetry yet" description="ARGUS and LYNX will appear after their first authenticated event is received." />}
    {products.length > 0 && <>
      <div className="product-tabs">{products.map((product) => <button type="button" className={selected?.id === product.id ? "active" : ""} onClick={() => setSelectedId(product.id)} key={product.id}><span className={`health-dot ${product.status}`} /><strong>{product.name}</strong><span>{product.status}</span></button>)}</div>
      {selected && <ProductDetails product={selected} />}
    </>}
  </div>;
}

function ProductDetails({ product }: { product: ProductSummary }) {
  return <div className="product-layout">
    <MetricGrid items={[
      { label: "Status", value: <Badge tone={product.status === "healthy" ? "good" : product.status === "degraded" ? "warn" : product.status === "down" ? "bad" : "neutral"}>{product.status}</Badge> },
      { label: "Runs today", value: formatNumber(product.runs_today) },
      { label: "Runs this month", value: formatNumber(product.runs_month) },
      { label: "Success rate", value: formatPercent(product.success_rate), tone: (product.success_rate ?? 0) >= .95 ? "good" : "warn" },
      { label: "Average runtime", value: `${formatNumber((product.average_duration_ms ?? 0) / 1000)}s` },
      { label: "API cost", value: formatMoney(product.api_cost_cents) },
      { label: "Average cost / run", value: formatMoney(product.average_cost_cents) },
      { label: "Active customers", value: formatNumber(product.active_customers) },
    ]} />
    <Panel title="Run reliability" subtitle="Completed versus failed runs"><div className="reliability"><div className="radial" style={{ "--progress": `${Math.round((product.success_rate ?? 0) * 100)}%` } as CSSProperties}><strong>{formatPercent(product.success_rate)}</strong><span>successful</span></div><dl><div><dt>Successful</dt><dd>{formatNumber(product.successful)}</dd></div><div><dt>Failed</dt><dd>{formatNumber(product.failed)}</dd></div><div><dt>Environment</dt><dd>{product.environment ?? "All"}</dd></div></dl></div></Panel>
    <Panel title="Top errors" subtitle="Most frequent failures in the selected period">{product.top_errors?.length ? <div className="error-bars">{product.top_errors.map((error) => <div key={error.label}><span>{error.label}</span><div><i style={{ width: `${Math.min(100, error.count * 10)}%` }} /></div><strong>{error.count}</strong></div>)}</div> : <p className="quiet-copy">No product errors recorded for this period.</p>}</Panel>
  </div>;
}
