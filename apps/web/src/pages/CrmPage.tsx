import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { Badge, EmptyState, ErrorState, FormActions, LoadingState, Modal, PageHeader, Panel, TableWrap, formatDate, submitObject, titleCase } from "../components/Workspace";
import { useAuth } from "../features/auth/AuthProvider";
import { createAccount, createContact, listAccounts, listContacts } from "../features/operations/api";
import type { Account, Contact } from "../features/operations/types";

export function CrmPage() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = params.get("view") === "contacts" ? "contacts" : "accounts";
  const q = params.get("q") ?? "";
  const page = Number(params.get("page") ?? 1);
  const [open, setOpen] = useState(false);
  const canWrite = Boolean(user?.permissions.some((permission) => ["sales:write_own", "sales:write_all"].includes(permission)));
  const accounts = useQuery({ queryKey: ["accounts", q, page], queryFn: () => listAccounts({ q, page, page_size: 25 }), enabled: tab === "accounts" });
  const contacts = useQuery({ queryKey: ["contacts", q, page], queryFn: () => listContacts({ q, page, page_size: 25 }), enabled: tab === "contacts" });
  const active = tab === "accounts" ? accounts : contacts;

  function updateParam(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    if (key !== "page") next.delete("page");
    setParams(next);
  }

  return <div className="workspace-page">
    <PageHeader eyebrow="Revenue records" title="CRM" description="Accounts and people in one searchable source of truth." actions={canWrite ? <button className="button primary" onClick={() => setOpen(true)} type="button">New {tab === "accounts" ? "account" : "contact"}</button> : undefined} />
    <div className="toolbar"><div className="segmented" role="tablist"><button className={tab === "accounts" ? "active" : ""} onClick={() => updateParam("view", "accounts")} role="tab" type="button">Accounts</button><button className={tab === "contacts" ? "active" : ""} onClick={() => updateParam("view", "contacts")} role="tab" type="button">Contacts</button></div><label className="search-field"><span aria-hidden="true">⌕</span><input aria-label={`Search ${tab}`} value={q} onChange={(event) => updateParam("q", event.target.value)} placeholder={`Search ${tab}…`} /></label></div>
    {active.isLoading && <LoadingState label={`Loading ${tab}`} />}
    {active.isError && <ErrorState error={active.error} retry={() => void active.refetch()} />}
    {tab === "accounts" && accounts.data && <AccountsTable items={accounts.data.items} />}
    {tab === "contacts" && contacts.data && <ContactsTable items={contacts.data.items} />}
    {active.data && active.data.total > 25 && <div className="pagination"><button disabled={page <= 1} onClick={() => updateParam("page", String(page - 1))} type="button">Previous</button><span>Page {page} · {active.data.total} records</span><button disabled={page * 25 >= active.data.total} onClick={() => updateParam("page", String(page + 1))} type="button">Next</button></div>}
    <CreateCrmModal kind={tab} open={open} onClose={() => setOpen(false)} />
  </div>;
}

function AccountsTable({ items }: { items: Account[] }) {
  if (!items.length) return <EmptyState title="No accounts found" description="Create the first prospect or adjust the search." />;
  return <Panel><TableWrap><table><thead><tr><th>Company</th><th>Type</th><th>Owner</th><th>Location</th><th>Score</th><th>Updated</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td><strong>{item.name}</strong><small>{item.domain ?? item.website ?? "No domain"}</small></td><td><Badge>{titleCase(item.account_type)}</Badge></td><td>{item.owner_name ?? "Unassigned"}</td><td>{[item.city, item.country].filter(Boolean).join(", ") || "—"}</td><td><strong>{item.lead_score ?? "—"}</strong></td><td>{formatDate(item.updated_at)}</td></tr>)}</tbody></table></TableWrap></Panel>;
}

function ContactsTable({ items }: { items: Contact[] }) {
  if (!items.length) return <EmptyState title="No contacts found" description="Add a decision maker or adjust the search." />;
  return <Panel><TableWrap><table><thead><tr><th>Contact</th><th>Company</th><th>Role</th><th>Channels</th><th>Decision maker</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td><strong>{item.first_name} {item.last_name}</strong><small>{item.email ?? "No email"}</small></td><td>{item.account_name ?? item.account_id}</td><td>{item.role ?? "—"}</td><td>{item.phone ?? titleCase(item.preferred_channel)}</td><td>{item.is_decision_maker ? <Badge tone="gold">Yes</Badge> : "—"}</td></tr>)}</tbody></table></TableWrap></Panel>;
}

function CreateCrmModal({ kind, open, onClose }: { kind: "accounts" | "contacts"; open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const mutation = useMutation<Account | Contact, Error, Partial<Account> | Partial<Contact>>({
    mutationFn: (body: Partial<Account> | Partial<Contact>) => kind === "accounts" ? createAccount(body as Partial<Account>) : createContact(body as Partial<Contact>),
    onSuccess: () => { onClose(); void queryClient.invalidateQueries({ queryKey: [kind] }); },
  });
  return <Modal title={kind === "accounts" ? "New account" : "New contact"} open={open} onClose={onClose}>
    <form className="record-form" onSubmit={(event) => {
      const values = submitObject(event);
      mutation.mutate(kind === "accounts" ? { ...values, lead_score: values.lead_score ? Number(values.lead_score) : undefined } : values);
    }}>
      {kind === "accounts" ? <>
        <label className="span-two">Company name<input name="name" required autoFocus /></label><label>Domain<input name="domain" placeholder="company.com" /></label><label>Industry<input name="industry" /></label><label>Account type<select name="account_type" required defaultValue="prospect_agency"><option value="prospect_agency">Prospect agency</option><option value="partner_agency">Partner agency</option><option value="direct_prospect">Direct prospect</option><option value="direct_customer">Direct customer</option><option value="case_study">Case study</option><option value="customer">Customer</option><option value="other">Other</option></select></label><label>Lead score<input name="lead_score" type="number" min="0" max="100" /></label><label>Country code<input name="country" maxLength={2} placeholder="IT" /></label><label>City<input name="city" /></label><label className="span-two">Notes<textarea name="notes" rows={3} /></label>
      </> : <>
        <label>First name<input name="first_name" required autoFocus /></label><label>Last name<input name="last_name" required /></label><label className="span-two">Account ID<input name="account_id" required /></label><label>Email<input name="email" type="email" /></label><label>Phone<input name="phone" type="tel" /></label><label>Role<input name="role" /></label><label>Preferred channel<select name="preferred_channel"><option value="email">Email</option><option value="phone">Phone</option><option value="linkedin">LinkedIn</option><option value="whatsapp">WhatsApp</option></select></label><label className="checkbox"><input name="is_decision_maker" type="checkbox" /> Decision maker</label>
      </>}
      {mutation.isError && <div className="form-error">{mutation.error.message}</div>}
      <FormActions saving={mutation.isPending} onCancel={onClose} />
    </form>
  </Modal>;
}
