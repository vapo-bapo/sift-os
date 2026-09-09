import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "./AuthProvider";
import type { Permission } from "./types";

export function AuthGuard() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") return <main className="status-page"><p>Loading your workspace…</p></main>;
  if (status === "forbidden") return <Navigate to="/access-denied" replace />;
  if (status === "anonymous") {
    return <Navigate to="/access-denied" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

export function PermissionGuard({ permission }: { permission: Permission }) {
  const { user } = useAuth();
  if (!user?.permissions.includes(permission)) return <Navigate to="/access-denied" replace />;
  return <Outlet />;
}
