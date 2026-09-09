import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { EmptyState, ErrorState, FormActions, LoadingState, MetricGrid, Modal, PageHeader, Panel, TableWrap, formatDate, formatMoney, submitObject, titleCase } from "../components/Workspace";
import { createFinanceEntry, createFinanceSnapshot, getFinanceMetrics, listFinanceEntries } from "../features/operations/api";
import type { FinanceEntry } from "../features/operations/types";

export function FinancePage() {
  const [modal, setModal] = useState<"entry" | "snapshot" | null>(null);
  const metrics = useQuery({ queryKey: ["finance", "metrics"], queryFn: getFinanceMetrics });
  const entries = useQuery({ queryKey: ["finance", "entries"], queryFn: listFinanceEntries });
  const m = metrics.data;
  return <div className="workspace-page">
    <PageHeader eyebrow="Management accounting" title="Finance" description="Internal operating visibility. This workspace does not replace official accounting." actions={<div className="button-row"><button className="button subtle" type="button" onClick={() => setModal("snapshot")}>Cash snapshot</button><button className="button primary" type="button" onClick={() => setModal("entry")}>New entry</button></div>} />
    {(metrics.isLoading || entries.isLoading) && <LoadingState label="Loading finance workspace" />}
    {(metrics.error || entries.error) && <ErrorState error={metrics.error ?? entries.error} retry={() => { void metrics.refetch(); void entries.refetch(); }} />}
    {m && <MetricGrid items={[
      { label: "Cash", value: formatMoney(m.cash_cents) }, { label: "Monthly burn", value: formatMoney(m.burn_cents), tone: "warn" }, { label: "MRR", value: formatMoney(m.mrr_cents), tone: "good" }, { label: "ARR", value: formatMoney(m.arr_cents) },
      { label: "Revenue MTD", value: formatMoney(m.revenue_mtd_cents) }, { label: "Costs MTD", value: formatMoney(m.cost_mtd_cents) }, { label: "Gross margin", value: formatMoney(m.gross_margin_cents) }, { label: "Weighted pipeline", value: formatMoney(m.weighted_pipeline_cents) },
      { label: "API / cloud", value: formatMoney(m.api_cloud_cost_cents) }, { label: "Partner commission due", value: formatMoney(m.partner_commission_accrued_cents) },
    ]} />}
    {entries.data && <Panel title="Financial entries" subtitle="Every change is recorded in the audit log">{entries.data.items.length ? <TableWrap><table><thead><tr><th>Date</th><th>Type</th><th>Category</th><th>Product</th><th>Source</th><th>Amount</th></tr></thead><tbody>{entries.data.items.map((entry) => <tr key={entry.id}><td>{formatDate(entry.date)}</td><td>{titleCase(entry.entry_type)}</td><td><strong>{entry.category}</strong><small>{entry.note ?? ""}</small></td><td>{entry.product ?? "—"}</td><td>{entry.source ?? "Manual"}</td><td className={entry.entry_type === "revenue" ? "positive-number" : "negative-number"}><strong>{formatMoney(entry.amount_cents, entry.currency)}</strong></td></tr>)}</tbody></table></TableWrap> : <EmptyState title="No finance entries" description="Add the first revenue or cost record. Amounts are stored safely in cents." />}</Panel>}
    <FinanceModal kind={modal} onClose={() => setModal(null)} />
  </div>;
}

function FinanceModal({ kind, onClose }: { kind: "entry" | "snapshot" | null; onClose: () => void }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => kind === "snapshot" ? createFinanceSnapshot(body as { date: string; cash_cents: number; currency: string; note?: string }) : createFinanceEntry(body as Partial<FinanceEntry>),
    onSuccess: () => { onClose(); void queryClient.invalidateQueries({ queryKey: ["finance"] }); },
  });
  return <Modal title={kind === "snapshot" ? "Cash snapshot" : "New financial entry"} description="Values are converted to integer cents before they leave your browser." open={kind !== null} onClose={onClose}><form className="record-form" onSubmit={(event) => { const value = submitObject(event); const cents = Math.round(Number(value.amount ?? 0) * 100); mutation.mutate(kind === "snapshot" ? { date: value.date, cash_cents: cents, currency: "EUR", note: value.note } : { ...value, amount_cents: cents, amount: undefined, currency: "EUR", recurring: Boolean(value.recurring) }); }}>
    <label>Date<input name="date" type="date" required defaultValue={new Date().toISOString().slice(0, 10)} /></label><label>Amount (€)<input name="amount" type="number" step="0.01" required autoFocus /></label>
    {kind === "entry" && <><label>Type<select name="entry_type"><option value="revenue">Revenue</option><option value="recurring_cost">Recurring cost</option><option value="one_time_cost">One-time cost</option><option value="api_cost">API cost</option><option value="cloud_cost">Cloud cost</option><option value="professional_service">Professional service</option><option value="partner_commission">Partner commission</option><option value="other">Other</option></select></label><label>Category<input name="category" required /></label><label>Product ID<input name="product_id" placeholder="Optional product UUID" /></label><label>Source<input name="source" placeholder="Invoice, manual…" /></label><label className="checkbox"><input name="recurring" type="checkbox" /> Recurring</label></>}
    <label className="span-two">Note<textarea name="note" rows={3} /></label>{mutation.isError && <div className="form-error">{mutation.error.message}</div>}<FormActions saving={mutation.isPending} onCancel={onClose} />
  </form></Modal>;
}
