import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { useAuth } from "../features/auth/AuthProvider";
import { AuthGuard, PermissionGuard } from "../features/auth/guards";
import type { Permission } from "../features/auth/types";
import { AccessDeniedPage } from "../pages/AccessDeniedPage";
import { DashboardPage } from "../pages/DashboardPage";
import { SsoCallbackPage } from "../pages/SsoCallbackPage";

function ShellLayout() {
  const { user, signOut } = useAuth();
  if (!user) return null;
  return <AppShell user={user} onSignOut={() => void signOut()}><RoutesContent /></AppShell>;
}

function LandingPage() {
  const { user } = useAuth();
  if (user?.roles.some((role) => role === "ceo" || role === "admin")) return <Navigate to="/cockpit" replace />;
  if (user?.roles.includes("sales_lead")) return <Navigate to="/sales" replace />;
  if (user?.roles.includes("sales")) return <Navigate to="/my-day" replace />;
  if (user?.roles.includes("coding")) return <Navigate to="/product-operations" replace />;
  return <Navigate to="/access-denied" replace />;
}

function GuardedPage({ permission, ...page }: { permission: Permission; title: string; eyebrow: string; description: string }) {
  const { user } = useAuth();
  if (!user?.permissions.includes(permission)) return <Navigate to="/access-denied" replace />;
  return <DashboardPage {...page} />;
}

function RoutesContent() {
  return (
    <Routes>
      <Route index element={<LandingPage />} />
      <Route path="cockpit" element={<GuardedPage permission="dashboard:company" title="Company cockpit" eyebrow="Leadership workspace" description="Your authenticated leadership workspace is ready." />} />
      <Route path="sales" element={<GuardedPage permission="dashboard:sales" title="Sales" eyebrow="Revenue workspace" description="Your sales workspace is ready." />} />
      <Route path="my-day" element={<GuardedPage permission="task:read" title="My day" eyebrow="Personal workspace" description="Your assigned-work workspace is ready." />} />
      <Route path="product-operations" element={<GuardedPage permission="product:read" title="Product operations" eyebrow="Product workspace" description="Your product workspace is ready." />} />
      <Route path="finance" element={<GuardedPage permission="finance:read" title="Finance" eyebrow="Finance workspace" description="Your finance workspace is ready." />} />
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
