import { Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";

import { AppShell } from "../components/AppShell";
import { useAuth } from "../features/auth/AuthProvider";
import { AuthGuard, PermissionGuard } from "../features/auth/guards";
import type { Permission } from "../features/auth/types";
import { AccessDeniedPage } from "../pages/AccessDeniedPage";
import { AdminPage } from "../pages/AdminPage";
import { CompanyPage } from "../pages/CompanyPage";
import { CrmPage } from "../pages/CrmPage";
import { DashboardPage } from "../pages/DashboardPage";
import { FinancePage } from "../pages/FinancePage";
import { LeaderboardPage } from "../pages/LeaderboardPage";
import { MyDayPage } from "../pages/MyDayPage";
import { PartnersPage } from "../pages/PartnersPage";
import { PipelinePage } from "../pages/PipelinePage";
import { ProductOperationsPage } from "../pages/ProductOperationsPage";
import { SsoCallbackPage } from "../pages/SsoCallbackPage";

function ShellLayout() {
  const { user, signOut } = useAuth();
  if (!user) return null;
  return <AppShell user={user} onSignOut={() => void signOut()}><RoutesContent /></AppShell>;
}

function LandingPage() {
  const { user } = useAuth();
  if (user?.roles.some((role) => role === "ceo" || role === "admin")) return <Navigate to="/dashboard" replace />;
  if (user?.roles.includes("sales_lead")) return <Navigate to="/dashboard" replace />;
  if (user?.roles.includes("sales")) return <Navigate to="/my-day" replace />;
  if (user?.roles.includes("coding")) return <Navigate to="/product-operations" replace />;
  return <Navigate to="/access-denied" replace />;
}

function GuardedPage({ permissions, children }: { permissions: Permission[]; children: ReactNode }) {
  const { user } = useAuth();
  if (!permissions.some((permission) => user?.permissions.includes(permission))) return <Navigate to="/access-denied" replace />;
  return children;
}

function RoutesContent() {
  return (
    <Routes>
      <Route index element={<LandingPage />} />
      <Route path="dashboard" element={<DashboardPage />} />
      <Route path="cockpit" element={<Navigate to="/dashboard" replace />} />
      <Route path="sales" element={<Navigate to="/dashboard" replace />} />
      <Route path="my-day" element={<GuardedPage permissions={["sales:read_own", "sales:read_all"]}><MyDayPage /></GuardedPage>} />
      <Route path="crm" element={<GuardedPage permissions={["sales:read_own", "sales:read_all"]}><CrmPage /></GuardedPage>} />
      <Route path="pipeline" element={<GuardedPage permissions={["sales:read_own", "sales:read_all"]}><PipelinePage /></GuardedPage>} />
      <Route path="leaderboard" element={<GuardedPage permissions={["dashboard:sales"]}><LeaderboardPage /></GuardedPage>} />
      <Route path="partners" element={<GuardedPage permissions={["partner:read", "partner:read_assigned"]}><PartnersPage /></GuardedPage>} />
      <Route path="product-operations" element={<GuardedPage permissions={["product:read"]}><ProductOperationsPage /></GuardedPage>} />
      <Route path="company" element={<GuardedPage permissions={["objective:read", "task:read"]}><CompanyPage /></GuardedPage>} />
      <Route path="finance" element={<GuardedPage permissions={["finance:read"]}><FinancePage /></GuardedPage>} />
      <Route path="admin" element={<GuardedPage permissions={["staff:manage"]}><AdminPage /></GuardedPage>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/auth/callback" element={<SsoCallbackPage />} />
      <Route path="/access-denied" element={<AccessDeniedPage />} />
      <Route element={<AuthGuard />}>
        <Route path="/*" element={<ShellLayout />} />
      </Route>
    </Routes>
  );
}

export { PermissionGuard };
