import { NavLink } from "react-router-dom";
import type { PropsWithChildren } from "react";

import type { MeResponse, Permission } from "../features/auth/types";
import { Brand } from "./Brand";

interface NavigationItem {
  label: string;
  to: string;
  permission: Permission;
}

const navigation: NavigationItem[] = [
  { label: "Cockpit", to: "/cockpit", permission: "dashboard:company" },
  { label: "Sales", to: "/sales", permission: "dashboard:sales" },
  { label: "My Day", to: "/my-day", permission: "task:read" },
  { label: "Product Operations", to: "/product-operations", permission: "product:read" },
  { label: "Finance", to: "/finance", permission: "finance:read" },
];

interface AppShellProps extends PropsWithChildren {
  user: MeResponse;
  onSignOut: () => void;
}

export function AppShell({ user, onSignOut, children }: AppShellProps) {
  const initials = user.display_name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
  const permittedNavigation = navigation.filter((item) => user.permissions.includes(item.permission));

  return (
    <div className="app-shell">
      <aside className="app-rail">
        <Brand />
        <nav aria-label="Primary navigation">
          {permittedNavigation.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => isActive ? "active" : undefined}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="rail-account">
          <span className="avatar" aria-hidden="true">{initials}</span>
          <span><strong>{user.display_name}</strong><small>{user.department}</small></span>
          <button type="button" onClick={onSignOut}>Sign out</button>
        </div>
      </aside>
      <main className="app-content">{children}</main>
    </div>
  );
}
