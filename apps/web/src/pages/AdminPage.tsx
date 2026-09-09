import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, EmptyState, ErrorState, LoadingState, Modal, PageHeader, Panel, TableWrap, formatDate, titleCase } from "../components/Workspace";
import { createProductCredential, itemsOf, listAudit, listProducts, listStaff, updateStaffRoles } from "../features/operations/api";
import type { StaffRole } from "../features/auth/types";

type Tab = "staff" | "audit" | "integrations";
const roles: StaffRole[] = ["ceo", "admin", "sales_lead", "sales", "coding"];

export function AdminPage() {
  const [tab, setTab] = useState<Tab>("staff");
  return <div className="workspace-page">
    <PageHeader eyebrow="Governance" title="Admin" description="People, integrations and immutable operational history." />
    <div className="toolbar"><div className="segmented"><button type="button" className={tab === "staff" ? "active" : ""} onClick={() => setTab("staff")}>Staff</button><button type="button" className={tab === "audit" ? "active" : ""} onClick={() => setTab("audit")}>Audit log</button><button type="button" className={tab === "integrations" ? "active" : ""} onClick={() => setTab("integrations")}>Integrations</button></div></div>
    {tab === "staff" && <StaffAdmin />}{tab === "audit" && <AuditAdmin />}{tab === "integrations" && <IntegrationsAdmin />}
  </div>;
}

function StaffAdmin() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["staff"], queryFn: listStaff });
  const mutation = useMutation({ mutationFn: ({ id, nextRoles }: { id: string; nextRoles: StaffRole[] }) => updateStaffRoles(id, nextRoles), onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["staff"] }) });
  if (query.isLoading) return <LoadingState label="Loading staff access" />;
  if (query.isError) return <ErrorState error={query.error} retry={() => void query.refetch()} />;
  return <Panel title="Staff access" subtitle="Backend permissions are derived from these roles">{query.data?.length ? <TableWrap><table><thead><tr><th>Staff member</th><th>Department</th><th>Roles</th><th>Status</th></tr></thead><tbody>{query.data.map((person) => <tr key={person.id}><td><strong>{person.display_name}</strong><small>{person.id}</small></td><td>{titleCase(person.department)}</td><td><div className="role-picker">{roles.map((role) => <label key={role}><input type="checkbox" checked={person.roles.includes(role)} disabled={mutation.isPending} onChange={(event) => { const nextRoles = event.target.checked ? [...person.roles, role] : person.roles.filter((item) => item !== role); mutation.mutate({ id: person.id, nextRoles }); }} />{titleCase(role)}</label>)}</div></td><td><Badge tone={person.active ? "good" : "bad"}>{person.active ? "Active" : "Inactive"}</Badge></td></tr>)}</tbody></table></TableWrap> : <EmptyState title="No staff members" description="Staff must first be mapped from SIFT Platform." />}</Panel>;
}

function AuditAdmin() {
  const query = useQuery({ queryKey: ["audit"], queryFn: listAudit });
  if (query.isLoading) return <LoadingState label="Loading immutable audit history" />;
  if (query.isError) return <ErrorState error={query.error} retry={() => void query.refetch()} />;
  return <Panel title="Audit log" subtitle="Security and business-critical changes">{query.data?.items.length ? <TableWrap><table><thead><tr><th>When</th><th>Actor</th><th>Action</th><th>Entity</th><th>ID</th></tr></thead><tbody>{query.data.items.map((item) => <tr key={item.id}><td>{formatDate(item.created_at, true)}</td><td>{item.actor_name ?? "System"}</td><td><Badge>{titleCase(item.action)}</Badge></td><td>{titleCase(item.entity_type)}</td><td><code>{item.entity_id ?? "—"}</code></td></tr>)}</tbody></table></TableWrap> : <EmptyState title="No audit activity" description="Role, finance, ownership and agreement changes will be recorded here." />}</Panel>;
}

function IntegrationsAdmin() {
  const products = useQuery({ queryKey: ["products"], queryFn: listProducts });
  const [credentialProduct, setCredentialProduct] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const create = useMutation({ mutationFn: ({ id, name }: { id: string; name: string }) => createProductCredential(id, name), onSuccess: (value) => { setCredentialProduct(null); setToken(value.token); } });
  if (products.isLoading) return <LoadingState label="Loading product integrations" />;
  if (products.isError) return <ErrorState error={products.error} retry={() => void products.refetch()} />;
  const items = itemsOf(products.data);
  return <><Panel title="Product integrations" subtitle="Separate service credentials for each event producer">{items.length ? <div className="integration-list">{items.map((product) => <article key={product.id}><div><span className={`health-dot ${product.status}`} /><div><strong>{product.name}</strong><p>{titleCase(product.status)} · {product.environment ?? "production"}</p></div></div><button className="button subtle" type="button" onClick={() => setCredentialProduct(product.id)}>Create credential</button></article>)}</div> : <EmptyState title="No products configured" description="Product integrations appear after their backend configuration is created." />}</Panel>
    <Modal title="Create service credential" description="The secret token is displayed only once." open={credentialProduct !== null} onClose={() => setCredentialProduct(null)}><form className="record-form" onSubmit={(event) => { event.preventDefault(); const name = new FormData(event.currentTarget).get("name"); create.mutate({ id: credentialProduct!, name: String(name) }); }}><label className="span-two">Credential name<input name="name" required autoFocus placeholder="ARGUS production" /></label>{create.isError && <div className="form-error">{create.error.message}</div>}<div className="form-actions"><button className="button subtle" type="button" onClick={() => setCredentialProduct(null)}>Cancel</button><button className="button primary" disabled={create.isPending} type="submit">{create.isPending ? "Creating…" : "Create"}</button></div></form></Modal>
    <Modal title="Copy this token now" description="For security, it cannot be viewed again after this dialog closes." open={token !== null} onClose={() => setToken(null)}><div className="secret-token"><code>{token}</code><button className="button primary" type="button" onClick={() => void navigator.clipboard.writeText(token ?? "")}>Copy token</button></div></Modal></>;
}
