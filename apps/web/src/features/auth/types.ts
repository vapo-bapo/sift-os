export type StaffRole = "ceo" | "admin" | "sales_lead" | "sales" | "coding";

export type Permission =
  | "dashboard:sales"
  | "dashboard:company"
  | "sales:read_all"
  | "sales:write_all"
  | "sales:assign"
  | "sales:read_own"
  | "sales:write_own"
  | "partner:read"
  | "partner:write"
  | "partner:read_assigned"
  | "task:read"
  | "task:write"
  | "task:write_own"
  | "product:read"
  | "objective:read"
  | "objective:write"
  | "finance:read"
  | "finance:write"
  | "audit:read"
  | "integration:manage"
  | "staff:manage";

export interface MeResponse {
  id: string;
  display_name: string;
  department: "sales" | "coding";
  roles: StaffRole[];
  permissions: Permission[];
}

export type AuthStatus = "loading" | "authenticated" | "anonymous" | "forbidden";
