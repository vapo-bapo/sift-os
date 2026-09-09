export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export type OpportunityStage =
  | "prospect" | "contacted" | "qualified" | "meeting" | "demo" | "proposal"
  | "negotiation" | "partner_signed" | "partner_activated" | "won" | "lost" | "disqualified";

export interface Account {
  id: string;
  name: string;
  domain?: string | null;
  website?: string | null;
  industry?: string | null;
  company_size?: string | null;
  country?: string | null;
  city?: string | null;
  account_type: string;
  source?: string | null;
  owner_id?: string | null;
  owner_name?: string | null;
  status: string;
  lead_score?: number | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Contact {
  id: string;
  account_id: string;
  account_name?: string | null;
  first_name: string;
  last_name: string;
  role?: string | null;
  email?: string | null;
  phone?: string | null;
  linkedin_url?: string | null;
  preferred_channel?: string | null;
  is_decision_maker: boolean;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Opportunity {
  id: string;
  account_id: string;
  account_name?: string | null;
  primary_contact_id?: string | null;
  owner_id?: string | null;
  owner_name?: string | null;
  stage: OpportunityStage;
  status: string;
  estimated_value_cents: number;
  weighted_value_cents: number;
  probability: number;
  expected_close_date?: string | null;
  source?: string | null;
  channel?: string | null;
  interested_products?: string[];
  next_action?: string | null;
  next_action_at?: string | null;
  stale?: boolean;
  created_at: string;
  updated_at: string;
}

export interface Activity {
  id: string;
  account_id?: string | null;
  account_name?: string | null;
  contact_id?: string | null;
  opportunity_id?: string | null;
  owner_id?: string | null;
  activity_type: string;
  outcome?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  notes?: string | null;
  next_action?: string | null;
  next_action_at?: string | null;
}

export interface MyDay {
  follow_ups_today: Activity[];
  overdue: Activity[];
  new_leads: Account[];
  meetings: Activity[];
  recent_activity: Activity[];
}

export interface LeaderboardRow {
  owner_id: string;
  owner_name: string;
  contacts: number;
  meetings: number;
  demos: number;
  proposals: number;
  signed: number;
  activated: number;
  won: number;
  revenue_cents: number;
  pipeline_cents?: number;
  weighted_pipeline_cents?: number;
  conversion_rate?: number;
}

export interface PartnerAgreement {
  id: string;
  effective_from: string;
  partner_share_bps: number;
  sift_share_bps: number;
  currency: string;
  status?: string;
}

export interface PartnerClient {
  id: string;
  partner_id: string;
  external_client_id: string;
  client_name: string;
  product?: string | null;
  plan?: string | null;
  gross_revenue_cents: number;
  partner_share_cents: number;
  sift_share_cents: number;
  currency: string;
  attributed_at: string;
  status?: string;
}

export interface Partner {
  id: string;
  name: string;
  legal_name?: string | null;
  email?: string | null;
  domain?: string | null;
  owner_staff_id?: string | null;
  owner_name?: string | null;
  status: string;
  onboarding_status?: string | null;
  enabled_products?: string[];
  notes?: string | null;
  agreement?: PartnerAgreement | null;
  clients?: PartnerClient[];
  total_mrr_cents?: number;
  total_revenue_cents?: number;
  commission_accrued_cents?: number;
  commission_paid_cents?: number;
}

export interface ProductSummary {
  id: string;
  code?: string;
  name: string;
  active?: boolean;
  status: "healthy" | "degraded" | "down" | "unknown" | string;
  environment?: string;
  runs_today?: number;
  runs_week?: number;
  runs_month?: number;
  successful?: number;
  failed?: number;
  success_rate?: number;
  average_duration_ms?: number;
  api_cost_cents?: number;
  average_cost_cents?: number;
  active_customers?: number;
  top_errors?: Array<{ label: string; count: number }>;
}

export interface Objective {
  id: string;
  title: string;
  description?: string | null;
  owner_id?: string | null;
  owner_name?: string | null;
  department: string;
  status: string;
  start_date?: string | null;
  due_date?: string | null;
  progress: number;
}

export interface WorkTask {
  id: string;
  title: string;
  description?: string | null;
  objective_id?: string | null;
  owner_id?: string | null;
  owner_name?: string | null;
  department: string;
  priority: "P0" | "P1" | "P2" | "P3" | string;
  status: string;
  due_date?: string | null;
  completed_at?: string | null;
}

export interface FinanceEntry {
  id: string;
  date: string;
  entry_type: string;
  category: string;
  amount_cents: number;
  currency: string;
  product?: string | null;
  recurring: boolean;
  source?: string | null;
  note?: string | null;
}

export interface FinanceMetrics {
  cash_cents?: number;
  burn_cents?: number;
  mrr_cents?: number;
  arr_cents?: number;
  revenue_mtd_cents?: number;
  cost_mtd_cents?: number;
  gross_margin_cents?: number;
  contracted_revenue_cents?: number;
  weighted_pipeline_cents?: number;
  api_cloud_cost_cents?: number;
  partner_commission_accrued_cents?: number;
  partner_commission_paid_cents?: number;
}

export interface Notification {
  id: string;
  title: string;
  body?: string | null;
  event_type?: string;
  entity_type?: string | null;
  entity_id?: string | null;
  created_at: string;
  read_at?: string | null;
  href?: string | null;
}

export interface SearchResult {
  id: string;
  type: "account" | "contact" | "partner" | "opportunity" | "task" | string;
  label: string;
  detail?: string | null;
  href?: string | null;
}

export interface AuditRecord {
  id: string;
  actor_name?: string | null;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  created_at: string;
  previous_value?: unknown;
  new_value?: unknown;
}

export type DashboardMetric = { label: string; value: number | string; format?: "currency" | "percent" | "number"; delta?: number };
export interface DashboardData {
  metrics?: DashboardMetric[];
  today?: DashboardMetric[] | Record<string, number>;
  sales?: Record<string, unknown>;
  finance?: Record<string, number>;
  tasks?: Record<string, number>;
  pipeline?: { total_cents?: number; weighted_cents?: number; stages?: Array<{ stage: string; count: number; value_cents: number }> };
  products?: ProductSummary[];
  activity?: Activity[];
  [key: string]: unknown;
}
