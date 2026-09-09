import type { FormEvent, PropsWithChildren, ReactNode } from "react";

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow: string; title: string; description: string; actions?: ReactNode }) {
  return <header className="page-header">
    <div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="page-description">{description}</p></div>
    {actions && <div className="page-actions">{actions}</div>}
  </header>;
}

export function Panel({ title, subtitle, action, children, className = "" }: PropsWithChildren<{ title?: string; subtitle?: string; action?: ReactNode; className?: string }>) {
  return <section className={`panel ${className}`}>
    {(title || action) && <header className="panel-header"><div>{title && <h2>{title}</h2>}{subtitle && <p>{subtitle}</p>}</div>{action}</header>}
    {children}
  </section>;
}

export function LoadingState({ label = "Loading live data" }: { label?: string }) {
  return <div className="state-card" role="status"><span className="spinner" aria-hidden="true"/><div><strong>{label}</strong><p>Connecting to the operational workspace…</p></div></div>;
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="state-card empty-state"><span className="state-symbol" aria-hidden="true">＋</span><div><strong>{title}</strong><p>{description}</p>{action}</div></div>;
}

export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  const message = error instanceof Error ? error.message : "The live data could not be loaded.";
  return <div className="state-card error-state" role="alert"><span className="state-symbol" aria-hidden="true">!</span><div><strong>Something went wrong</strong><p>{message}</p>{retry && <button className="button subtle" type="button" onClick={retry}>Try again</button>}</div></div>;
}

export function MetricGrid({ items }: { items: Array<{ label: string; value: ReactNode; detail?: string; tone?: "good" | "warn" | "bad" }> }) {
  return <div className="metric-grid">{items.map((item) => <article className={`metric-card ${item.tone ?? ""}`} key={item.label}>
    <span>{item.label}</span><strong>{item.value}</strong>{item.detail && <small>{item.detail}</small>}
  </article>)}</div>;
}

export function Badge({ children, tone = "neutral" }: PropsWithChildren<{ tone?: "neutral" | "good" | "warn" | "bad" | "gold" }>) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function Modal({ title, description, open, onClose, children }: PropsWithChildren<{ title: string; description?: string; open: boolean; onClose: () => void }>) {
  if (!open) return null;
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <header><div><p className="eyebrow">Create record</p><h2 id="modal-title">{title}</h2>{description && <p>{description}</p>}</div><button className="icon-button" aria-label="Close" type="button" onClick={onClose}>×</button></header>
      {children}
    </section>
  </div>;
}

export function FormActions({ saving, onCancel }: { saving: boolean; onCancel: () => void }) {
  return <div className="form-actions"><button className="button subtle" type="button" onClick={onCancel}>Cancel</button><button className="button primary" type="submit" disabled={saving}>{saving ? "Saving…" : "Save"}</button></div>;
}

export function submitObject(event: FormEvent<HTMLFormElement>): Record<string, string | boolean> {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  return Object.fromEntries(Array.from(data.entries()).flatMap(([key, value]) => {
    const normalized = value === "on" ? true : String(value).trim();
    return normalized === "" ? [] : [[key, normalized]];
  }));
}

export function formatMoney(cents: number | null | undefined, currency = "EUR") {
  return new Intl.NumberFormat("it-IT", { style: "currency", currency, maximumFractionDigits: 0 }).format((cents ?? 0) / 100);
}

export function formatNumber(value: number | null | undefined) {
  return new Intl.NumberFormat("it-IT", { maximumFractionDigits: 1 }).format(value ?? 0);
}

export function formatPercent(value: number | null | undefined) {
  const normalized = (value ?? 0) > 1 ? (value ?? 0) / 100 : value ?? 0;
  return new Intl.NumberFormat("it-IT", { style: "percent", maximumFractionDigits: 1 }).format(normalized);
}

export function formatDate(value: string | null | undefined, withTime = false) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("it-IT", { day: "2-digit", month: "short", ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}) }).format(date);
}

export function titleCase(value: string | null | undefined) {
  return (value ?? "—").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function TableWrap({ children }: PropsWithChildren) { return <div className="table-wrap">{children}</div>; }
