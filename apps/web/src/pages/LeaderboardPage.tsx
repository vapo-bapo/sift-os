import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { Badge, EmptyState, ErrorState, LoadingState, PageHeader, Panel, TableWrap, formatMoney, formatPercent } from "../components/Workspace";
import { getLeaderboard, itemsOf } from "../features/operations/api";

const ranges = [{ value: "today", label: "Today" }, { value: "week", label: "This week" }, { value: "last_week", label: "Last week" }, { value: "month", label: "Month" }, { value: "quarter", label: "Quarter" }];

export function LeaderboardPage() {
  const [params, setParams] = useSearchParams();
  const range = params.get("range") ?? "month";
  const bounds = dateBounds(range);
  const query = useQuery({ queryKey: ["leaderboard", range], queryFn: () => getLeaderboard(bounds.start, bounds.end) });
  const rows = itemsOf(query.data);
  return <div className="workspace-page">
    <PageHeader eyebrow="Sales performance" title="Leaderboard" description="Volume and conversion efficiency together—never activity for activity's sake." />
    <div className="toolbar"><div className="segmented wrap">{ranges.map((item) => <button key={item.value} type="button" className={range === item.value ? "active" : ""} onClick={() => setParams({ range: item.value })}>{item.label}</button>)}</div></div>
    {query.isLoading && <LoadingState label="Calculating team performance" />}
    {query.isError && <ErrorState error={query.error} retry={() => void query.refetch()} />}
    {query.data && !rows.length && <EmptyState title="No performance data yet" description="Completed activities and stage movement will populate this view." />}
    {rows.length > 0 && <Panel><TableWrap><table className="leaderboard-table"><thead><tr><th>#</th><th>Sales</th><th>Contacts</th><th>Meetings</th><th>Demos</th><th>Proposals</th><th>Signed</th><th>Activated</th><th>Won</th><th>Efficiency</th><th>Revenue</th></tr></thead><tbody>{rows.map((row, index) => <tr key={row.owner_id}><td><span className={`rank rank-${index + 1}`}>{index + 1}</span></td><td><strong>{row.owner_name}</strong><small>{formatMoney(row.weighted_pipeline_cents)} weighted</small></td><td>{row.contacts}</td><td>{row.meetings}</td><td>{row.demos}</td><td>{row.proposals}</td><td>{row.signed}</td><td>{row.activated}</td><td><Badge tone="good">{row.won}</Badge></td><td>{formatPercent(row.conversion_rate)}</td><td><strong>{formatMoney(row.revenue_cents)}</strong></td></tr>)}</tbody></table></TableWrap></Panel>}
  </div>;
}

function dateBounds(range: string) {
  const end = new Date();
  const start = new Date(end);
  if (range === "today") start.setHours(0, 0, 0, 0);
  else if (range === "week") start.setDate(start.getDate() - 7);
  else if (range === "last_week") { end.setDate(end.getDate() - 7); start.setDate(start.getDate() - 14); }
  else if (range === "quarter") start.setMonth(start.getMonth() - 3);
  else start.setMonth(start.getMonth() - 1);
  return { start: start.toISOString(), end: end.toISOString() };
}
