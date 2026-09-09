import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { Badge, EmptyState, ErrorState, FormActions, LoadingState, Modal, PageHeader, Panel, TableWrap, formatDate, formatMoney, submitObject, titleCase } from "../components/Workspace";
import { useAuth } from "../features/auth/AuthProvider";
import { createOpportunity, listAccounts, listOpportunities, moveOpportunity } from "../features/operations/api";
import type { Opportunity, OpportunityStage } from "../features/operations/types";

const stages: OpportunityStage[] = ["prospect", "contacted", "qualified", "meeting", "demo", "proposal", "negotiation", "partner_signed", "partner_activated", "won", "lost", "disqualified"];

export function PipelinePage() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const view = params.get("view") === "table" ? "table" : "kanban";
  const q = params.get("q") ?? "";
  const stage = params.get("stage") ?? "";
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const canWrite = Boolean(user?.permissions.some((permission) => ["sales:write_own", "sales:write_all"].includes(permission)));
  const query = useQuery({ queryKey: ["opportunities", q, stage], queryFn: () => listOpportunities({ q, stage, page_size: 100 }) });
  const accountQuery = useQuery({ queryKey: ["accounts", "pipeline-names"], queryFn: () => listAccounts({ page_size: 100 }) });
  const move = useMutation({ mutationFn: ({ id, next }: { id: string; next: OpportunityStage }) => moveOpportunity(id, next), onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["opportunities"] }) });
  const set = (key: string, value: string) => { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); setParams(next); };
  const accountNames = new Map((accountQuery.data?.items ?? []).map((account) => [account.id, account.name]));
  const opportunities = (query.data?.items ?? []).map((item) => ({ ...item, account_name: item.account_name ?? accountNames.get(item.account_id) }));

  return <div className="workspace-page wide-page">
    <PageHeader eyebrow="Sales execution" title="Pipeline" description="Move every opportunity forward with its value, owner and next action visible." actions={canWrite ? <button className="button primary" type="button" onClick={() => setOpen(true)}>New opportunity</button> : undefined} />
    <div className="toolbar"><div className="segmented"><button className={view === "kanban" ? "active" : ""} onClick={() => set("view", "kanban")} type="button">Kanban</button><button className={view === "table" ? "active" : ""} onClick={() => set("view", "table")} type="button">Table</button></div><label className="search-field"><span>⌕</span><input aria-label="Search pipeline" value={q} onChange={(event) => set("q", event.target.value)} placeholder="Search company or next action…" /></label>{view === "table" && <select aria-label="Filter by stage" value={stage} onChange={(event) => set("stage", event.target.value)}><option value="">All stages</option>{stages.map((value) => <option key={value} value={value}>{titleCase(value)}</option>)}</select>}</div>
    {query.isLoading && <LoadingState label="Loading the pipeline" />}
    {query.isError && <ErrorState error={query.error} retry={() => void query.refetch()} />}
    {query.data && !opportunities.length && <EmptyState title="No opportunities in this view" description="Create the first deal or clear the active filters." />}
    {query.data && opportunities.length > 0 && view === "kanban" && <Kanban opportunities={opportunities} canMove={canWrite} onMove={(id, next) => move.mutate({ id, next })} />}
    {query.data && opportunities.length > 0 && view === "table" && <OpportunityTable items={opportunities} />}
    {move.isError && <div className="toast error-state" role="alert">Stage change failed: {move.error.message}</div>}
    <CreateOpportunityModal open={open} onClose={() => setOpen(false)} />
  </div>;
}

function Kanban({ opportunities, canMove, onMove }: { opportunities: Opportunity[]; canMove: boolean; onMove: (id: string, stage: OpportunityStage) => void }) {
  const grouped = useMemo(() => Object.fromEntries(stages.map((stage) => [stage, opportunities.filter((item) => item.stage === stage)])) as Record<OpportunityStage, Opportunity[]>, [opportunities]);
  return <div className="kanban" aria-label="Opportunity pipeline">{stages.map((stage) => {
    const items = grouped[stage]; const total = items.reduce((sum, item) => sum + item.estimated_value_cents, 0);
    return <section className="kanban-column" key={stage} onDragOver={(event) => { if (canMove) event.preventDefault(); }} onDrop={(event) => { const id = event.dataTransfer.getData("text/opportunity-id"); if (id && canMove) onMove(id, stage); }}>
      <header><div><strong>{titleCase(stage)}</strong><span>{items.length}</span></div><small>{formatMoney(total)}</small></header>
      <div className="kanban-stack">{items.map((item) => <article className={`deal-card ${item.stale ? "stale" : ""}`} key={item.id} draggable={canMove} onDragStart={(event) => event.dataTransfer.setData("text/opportunity-id", item.id)}>
        <div><Badge tone={item.stale ? "warn" : "neutral"}>{item.stale ? "Stale" : `${item.probability}%`}</Badge><strong>{item.account_name ?? item.account_id}</strong></div><p>{item.next_action ?? "Next action not set"}</p><footer><span>{item.owner_name ?? item.owner_id ?? "Unassigned"}</span><strong>{formatMoney(item.estimated_value_cents)}</strong></footer>
      </article>)}</div>
    </section>;
  })}</div>;
}

function OpportunityTable({ items }: { items: Opportunity[] }) {
  return <Panel><TableWrap><table><thead><tr><th>Account</th><th>Stage</th><th>Value</th><th>Weighted</th><th>Owner</th><th>Next action</th><th>Close</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td><strong>{item.account_name ?? item.account_id}</strong><small>{titleCase(item.channel)}</small></td><td><Badge tone={item.stale ? "warn" : item.stage === "won" ? "good" : "neutral"}>{item.stale ? "Stale · " : ""}{titleCase(item.stage)}</Badge></td><td>{formatMoney(item.estimated_value_cents)}</td><td>{formatMoney(item.weighted_value_cents)}</td><td>{item.owner_name ?? item.owner_id ?? "Unassigned"}</td><td>{item.next_action ?? "—"}<small>{formatDate(item.next_action_at, true)}</small></td><td>{formatDate(item.expected_close_date)}</td></tr>)}</tbody></table></TableWrap></Panel>;
}

function CreateOpportunityModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({ mutationFn: createOpportunity, onSuccess: () => { onClose(); void queryClient.invalidateQueries({ queryKey: ["opportunities"] }); } });
  return <Modal title="New opportunity" description="Create a real pipeline record linked to an account." open={open} onClose={onClose}><form className="record-form" onSubmit={(event) => {
    const value = submitObject(event);
    mutation.mutate({ ...value, estimated_value_cents: Math.round(Number(value.estimated_value ?? 0) * 100), probability: Number(value.probability ?? 10), interested_products: String(value.interested_products ?? "").split(",").map((entry) => entry.trim()).filter(Boolean), estimated_value: undefined } as Partial<Opportunity> & { estimated_value?: undefined });
  }}>
    <label className="span-two">Account ID<input name="account_id" required autoFocus /></label><label>Stage<select name="stage" defaultValue="prospect">{stages.map((value) => <option key={value} value={value}>{titleCase(value)}</option>)}</select></label><label>Channel<select name="channel" defaultValue="agency_partner"><option value="agency_partner">Agency partner</option><option value="direct_sales">Direct sales</option><option value="referral">Referral</option><option value="inbound">Inbound</option><option value="other">Other</option></select></label><label>Estimated value (€)<input name="estimated_value" type="number" min="0" step="0.01" required /></label><label>Probability %<input name="probability" type="number" min="0" max="100" defaultValue="10" /></label><label>Expected close<input name="expected_close_date" type="date" /></label><label>Products<input name="interested_products" placeholder="ARGUS, LYNX" /></label><label className="span-two">Next action<input name="next_action" required /></label><label>Follow-up<input name="next_action_at" type="datetime-local" /></label>
    {mutation.isError && <div className="form-error">{mutation.error.message}</div>}<FormActions saving={mutation.isPending} onCancel={onClose} />
  </form></Modal>;
}
