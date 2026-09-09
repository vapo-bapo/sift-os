import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, EmptyState, ErrorState, FormActions, LoadingState, MetricGrid, Modal, PageHeader, formatDate, formatMoney, formatPercent, submitObject, titleCase } from "../components/Workspace";
import { useAuth } from "../features/auth/AuthProvider";
import { createAgreement, createPartner, createPartnerClient, getPartnerMetrics, itemsOf, listPartners } from "../features/operations/api";
import type { Partner } from "../features/operations/types";

export function PartnersPage() {
  const { user } = useAuth();
  const [createOpen, setCreateOpen] = useState(false);
  const [selected, setSelected] = useState<Partner | null>(null);
  const partners = useQuery({ queryKey: ["partners"], queryFn: listPartners });
  const metrics = useQuery({ queryKey: ["partners", "metrics"], queryFn: getPartnerMetrics });
  const items = itemsOf(partners.data);
  const canWrite = Boolean(user?.permissions.some((permission) => ["partner:write", "sales:write_all"].includes(permission)));
  const metricItems = Object.entries(metrics.data ?? {}).slice(0, 8).map(([key, value]) => ({ label: titleCase(key), value: key.includes("cents") ? formatMoney(value) : key.includes("rate") ? formatPercent(value) : value }));

  return <div className="workspace-page">
    <PageHeader eyebrow="Agency network" title="Partners" description="Agreements, activation and customer revenue in one accountable lifecycle." actions={canWrite ? <button className="button primary" type="button" onClick={() => setCreateOpen(true)}>New partner</button> : undefined} />
    {metricItems.length > 0 && <MetricGrid items={metricItems} />}
    {partners.isLoading && <LoadingState label="Loading partner network" />}
    {partners.isError && <ErrorState error={partners.error} retry={() => void partners.refetch()} />}
    {partners.data && !items.length && <EmptyState title="No partners yet" description="Create the first agency partner to begin tracking its lifecycle." action={canWrite ? <button className="button subtle" onClick={() => setCreateOpen(true)} type="button">Create partner</button> : undefined} />}
    {items.length > 0 && <div className="partner-grid">{items.map((partner) => <button className="partner-card" type="button" key={partner.id} onClick={() => setSelected(partner)}>
      <header><span className="partner-monogram">{partner.name.slice(0, 2).toUpperCase()}</span><Badge tone={partner.status === "active" ? "good" : partner.status === "signed" || partner.status === "onboarding" ? "gold" : "neutral"}>{titleCase(partner.status)}</Badge></header>
      <h2>{partner.name}</h2><p>{partner.domain ?? partner.email ?? "No contact details"}</p>
      <dl><div><dt>MRR</dt><dd>{formatMoney(partner.total_mrr_cents)}</dd></div><div><dt>Clients</dt><dd>{partner.clients?.length ?? 0}</dd></div><div><dt>Partner share</dt><dd>{partner.agreement ? formatPercent(partner.agreement.partner_share_bps / 10000) : "—"}</dd></div></dl>
      <footer><span>{partner.owner_name ?? "Unassigned"}</span><span>View details →</span></footer>
    </button>)}</div>}
    <CreatePartnerModal open={createOpen} onClose={() => setCreateOpen(false)} />
    <PartnerDrawer partner={selected} canWrite={canWrite} onClose={() => setSelected(null)} />
  </div>;
}

function CreatePartnerModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({ mutationFn: createPartner, onSuccess: () => { onClose(); void queryClient.invalidateQueries({ queryKey: ["partners"] }); } });
  return <Modal title="New agency partner" open={open} onClose={onClose}><form className="record-form" onSubmit={(event) => mutation.mutate(submitObject(event) as Partial<Partner>)}><label>Trading name<input name="name" required autoFocus /></label><label>Legal name<input name="legal_name" /></label><label>Email<input name="email" type="email" /></label><label>Domain<input name="domain" /></label><label>Owner staff ID<input name="owner_staff_id" /></label><label>Status<select name="status" defaultValue="prospect"><option value="prospect">Prospect</option><option value="negotiating">Negotiating</option><option value="signed">Signed</option><option value="onboarding">Onboarding</option><option value="active">Active</option></select></label><label className="span-two">Notes<textarea name="notes" rows={3} /></label>{mutation.isError && <div className="form-error">{mutation.error.message}</div>}<FormActions saving={mutation.isPending} onCancel={onClose} /></form></Modal>;
}

function PartnerDrawer({ partner, canWrite, onClose }: { partner: Partner | null; canWrite: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"agreement" | "client" | null>(null);
  const agreement = useMutation({ mutationFn: (body: { effective_from: string; partner_share_bps: number; sift_share_bps: number; currency: string; terms?: string }) => createAgreement(partner!.id, body), onSuccess: () => { setMode(null); void queryClient.invalidateQueries({ queryKey: ["partners"] }); } });
  const client = useMutation({ mutationFn: (body: Record<string, unknown>) => createPartnerClient(partner!.id, body), onSuccess: () => { setMode(null); void queryClient.invalidateQueries({ queryKey: ["partners"] }); } });
  if (!partner) return null;
  return <div className="drawer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><aside className="drawer" aria-label={`${partner.name} details`}>
    <header><div><p className="eyebrow">Partner record</p><h2>{partner.name}</h2><p>{partner.legal_name ?? partner.domain ?? "Agency partner"}</p></div><button className="icon-button" type="button" aria-label="Close" onClick={onClose}>×</button></header>
    <div className="drawer-metrics"><div><span>Status</span><strong>{titleCase(partner.status)}</strong></div><div><span>Total MRR</span><strong>{formatMoney(partner.total_mrr_cents)}</strong></div><div><span>Total revenue</span><strong>{formatMoney(partner.total_revenue_cents)}</strong></div><div><span>Commission accrued</span><strong>{formatMoney(partner.commission_accrued_cents)}</strong></div></div>
    <section><div className="section-heading"><h3>Agreement</h3>{canWrite && <button type="button" onClick={() => setMode("agreement")}>New version</button>}</div>{partner.agreement ? <div className="agreement-card"><strong>{formatPercent(partner.agreement.partner_share_bps / 10000)} partner / {formatPercent(partner.agreement.sift_share_bps / 10000)} SIFT</strong><span>Effective {formatDate(partner.agreement.effective_from)}</span></div> : <p className="quiet-copy">No agreement recorded.</p>}</section>
    <section><div className="section-heading"><h3>Attributed clients</h3>{canWrite && <button type="button" onClick={() => setMode("client")}>Add client</button>}</div>{partner.clients?.length ? <div className="client-list">{partner.clients.map((item) => <article key={item.id}><div><strong>{item.client_name}</strong><span>{item.product ?? "Product not set"}</span></div><div><strong>{formatMoney(item.gross_revenue_cents)}</strong><span>{formatMoney(item.partner_share_cents)} partner share</span></div></article>)}</div> : <p className="quiet-copy">The first attributed customer activates the partner.</p>}</section>
    {mode === "agreement" && <form className="inline-form" onSubmit={(event) => { const value = submitObject(event); const share = Math.round(Number(value.partner_share_percent) * 100); agreement.mutate({ effective_from: String(value.effective_from), partner_share_bps: share, sift_share_bps: 10000 - share, currency: "EUR", terms: String(value.terms ?? "") }); }}><h3>Agreement version</h3><label>Effective from<input name="effective_from" type="date" required /></label><label>Partner share %<input name="partner_share_percent" type="number" min="0" max="100" step="0.01" required /></label><label>Terms<textarea name="terms" rows={2} /></label><FormActions saving={agreement.isPending} onCancel={() => setMode(null)} /></form>}
    {mode === "client" && <form className="inline-form" onSubmit={(event) => { const value = submitObject(event); client.mutate({ ...value, gross_revenue_cents: Math.round(Number(value.gross_revenue ?? 0) * 100), gross_revenue: undefined, currency: "EUR" }); }}><h3>Attribute client</h3><label>External client ID<input name="external_client_id" required /></label><label>Client name<input name="client_name" required /></label><label>Product<input name="product" /></label><label>Gross revenue (€)<input name="gross_revenue" type="number" step="0.01" min="0" required /></label><FormActions saving={client.isPending} onCancel={() => setMode(null)} /></form>}
  </aside></div>;
}
