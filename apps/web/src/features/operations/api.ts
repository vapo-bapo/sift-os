import { apiRequest } from "../auth/api";
import type { MeResponse, StaffRole } from "../auth/types";
import type {
  Account, Activity, AuditRecord, Contact, DashboardData, FinanceEntry, FinanceMetrics, LeaderboardRow,
  MyDay, Notification, Objective, Opportunity, OpportunityStage, Page, Partner, ProductSummary, SearchResult, WorkTask,
} from "./types";

type QueryValue = string | number | boolean | null | undefined;
function withQuery(path: string, query: Record<string, QueryValue> = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  });
  const suffix = params.toString();
  return suffix ? `${path}?${suffix}` : path;
}

function json(method: string, body?: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) };
}

export type ListQuery = { q?: string; page?: number; page_size?: number; owner_id?: string; stage?: string; status?: string; source?: string };
function crmQuery(query: ListQuery & { account_id?: string } = {}) {
  const { q, ...rest } = query;
  return { ...rest, search: q };
}
export const listAccounts = (query: ListQuery = {}) => apiRequest<Page<Account>>(withQuery("/accounts", crmQuery(query)));
export const createAccount = (body: Partial<Account>) => apiRequest<Account>("/accounts", json("POST", body));
export const updateAccount = (id: string, body: Partial<Account>) => apiRequest<Account>(`/accounts/${id}`, json("PATCH", body));
export const archiveAccount = (id: string) => apiRequest<void>(`/accounts/${id}/archive`, json("POST"));
export const listContacts = (query: ListQuery & { account_id?: string } = {}) => apiRequest<Page<Contact>>(withQuery("/contacts", crmQuery(query)));
export const createContact = (body: Partial<Contact>) => apiRequest<Contact>("/contacts", json("POST", body));
export const updateContact = (id: string, body: Partial<Contact>) => apiRequest<Contact>(`/contacts/${id}`, json("PATCH", body));
export const listOpportunities = (query: ListQuery = {}) => apiRequest<Page<Opportunity>>(withQuery("/opportunities", crmQuery(query)));
export const createOpportunity = (body: Partial<Opportunity>) => apiRequest<Opportunity>("/opportunities", json("POST", body));
export const updateOpportunity = (id: string, body: Partial<Opportunity>) => apiRequest<Opportunity>(`/opportunities/${id}`, json("PATCH", body));
export const moveOpportunity = (id: string, stage: OpportunityStage) => apiRequest<Opportunity>(`/opportunities/${id}/stage`, json("POST", { stage }));
export const assignOpportunity = (id: string, owner_id: string) => apiRequest<Opportunity>(`/opportunities/${id}/assign`, json("POST", { owner_id }));
export const listActivities = (query: ListQuery & { due?: string } = {}) => apiRequest<Page<Activity>>(withQuery("/activities", query));
export const createActivity = (body: Partial<Activity>) => apiRequest<Activity>("/activities", json("POST", body));
export const updateActivity = (id: string, body: Partial<Activity>) => apiRequest<Activity>(`/activities/${id}`, json("PATCH", body));
export const getMyDay = () => apiRequest<MyDay>("/sales/my-day");
export const getPipeline = () => apiRequest<{ items?: Opportunity[]; stages?: Record<string, Opportunity[]> }>("/sales/pipeline");
export const getLeaderboard = (start?: string, end?: string) => apiRequest<Page<LeaderboardRow> | LeaderboardRow[]>(withQuery("/sales/leaderboard", { start, end }));

export const listPartners = () => apiRequest<Page<Partner> | Partner[]>("/partners");
export const createPartner = (body: Partial<Partner>) => apiRequest<Partner>("/partners", json("POST", body));
export const updatePartner = (id: string, body: Partial<Partner>) => apiRequest<Partner>(`/partners/${id}`, json("PATCH", body));
export const archivePartner = (id: string) => apiRequest<void>(`/partners/${id}/archive`, json("POST"));
export const createAgreement = (id: string, body: { effective_from: string; partner_share_bps: number; sift_share_bps: number; currency: string; terms?: string }) => apiRequest<Partner>(`/partners/${id}/agreements`, json("POST", body));
export const createPartnerClient = (id: string, body: Record<string, unknown>) => apiRequest<Partner>(`/partners/${id}/clients`, json("POST", body));
export const getPartnerMetrics = () => apiRequest<Record<string, number>>("/partners/metrics");

export const listProducts = () => apiRequest<Page<ProductSummary> | ProductSummary[]>("/products");
export async function getProductMetrics(): Promise<ProductSummary[]> {
  const [productsValue, metricsValue] = await Promise.all([
    apiRequest<Array<{ id: string; code: string; name: string; active: boolean }>>("/products"),
    apiRequest<Array<{ product_id: string; code: string; runs_total: number; runs_running: number; runs_succeeded: number; runs_failed: number; events_total: number; cost_cents: number; units: number }>>("/products/metrics"),
  ]);
  return productsValue.map((product) => {
    const metric = metricsValue.find((item) => item.product_id === product.id || item.code === product.code);
    const completed = (metric?.runs_succeeded ?? 0) + (metric?.runs_failed ?? 0);
    return { id: product.id, code: product.code, name: product.name, active: product.active, status: !product.active ? "down" : (metric?.runs_failed ?? 0) > 0 ? "degraded" : completed > 0 ? "healthy" : "unknown", runs_today: metric?.runs_total ?? 0, runs_month: metric?.runs_total ?? 0, successful: metric?.runs_succeeded ?? 0, failed: metric?.runs_failed ?? 0, success_rate: completed ? (metric?.runs_succeeded ?? 0) / completed : 0, api_cost_cents: metric?.cost_cents ?? 0, active_customers: metric?.units ?? 0 };
  });
}
export const getDashboard = () => apiRequest<DashboardData>("/dashboard");
export const getSalesDashboard = () => apiRequest<DashboardData>("/dashboard/sales");
export const getProductsDashboard = () => apiRequest<DashboardData>("/dashboard/products");
export const getFinanceDashboard = () => apiRequest<DashboardData>("/dashboard/finance");

export const listObjectives = () => apiRequest<Page<Objective>>("/objectives");
export const createObjective = (body: Partial<Objective>) => apiRequest<Objective>("/objectives", json("POST", body));
export const updateObjective = (id: string, body: Partial<Objective>) => apiRequest<Objective>(`/objectives/${id}`, json("PATCH", body));
export const listTasks = () => apiRequest<Page<WorkTask>>("/tasks");
export const createTask = (body: Partial<WorkTask>) => apiRequest<WorkTask>("/tasks", json("POST", body));
export const updateTask = (id: string, body: Partial<WorkTask>) => apiRequest<WorkTask>(`/tasks/${id}`, json("PATCH", body));

export const listFinanceEntries = () => apiRequest<Page<FinanceEntry>>("/finance/entries");
export const createFinanceEntry = (body: Partial<FinanceEntry>) => apiRequest<FinanceEntry>("/finance/entries", json("POST", body));
export const updateFinanceEntry = (id: string, body: Partial<FinanceEntry>) => apiRequest<FinanceEntry>(`/finance/entries/${id}`, json("PATCH", body));
export const createFinanceSnapshot = (body: { date: string; cash_cents: number; currency: string; note?: string }) => apiRequest("/finance/snapshots", json("POST", body));
export const getFinanceMetrics = () => apiRequest<FinanceMetrics>("/finance/metrics");

export const listNotifications = () => apiRequest<{ items: Notification[]; unread: number }>("/notifications");
export const readNotification = (id: string) => apiRequest<Notification>(`/notifications/${id}/read`, json("PATCH"));
export async function searchEverything(q: string): Promise<Page<SearchResult>> {
  const grouped = await apiRequest<Record<string, SearchResult[]>>(withQuery("/search", { q: q.trim() }));
  const items = Object.values(grouped).flat().slice(0, 12);
  return { items, total: items.length, page: 1, page_size: 12 };
}
export const listAudit = () => apiRequest<Page<AuditRecord>>("/admin/audit");
export const listStaff = () => apiRequest<Array<MeResponse & { active: boolean }>>("/staff");
export const updateStaffRoles = (id: string, roles: StaffRole[]) => apiRequest<MeResponse & { active: boolean }>(`/staff/${id}/roles`, json("PATCH", { roles }));
export const createProductCredential = (id: string, name: string) => apiRequest<{ id: string; name: string; token: string }>(`/products/${id}/credentials`, json("POST", { name }));
export const rotateProductCredential = (productId: string, credentialId: string) => apiRequest<{ id: string; name: string; token: string }>(`/products/${productId}/credentials/${credentialId}/rotate`, json("POST"));
export const revokeProductCredential = (productId: string, credentialId: string) => apiRequest<void>(`/products/${productId}/credentials/${credentialId}/revoke`, json("POST"));

export function itemsOf<T>(value: Page<T> | T[] | undefined): T[] {
  return Array.isArray(value) ? value : value?.items ?? [];
}
