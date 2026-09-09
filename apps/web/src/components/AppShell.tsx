import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import type { PropsWithChildren } from "react";

import type { MeResponse, Permission } from "../features/auth/types";
import { itemsOf, listNotifications, readNotification, searchEverything } from "../features/operations/api";
import { formatDate, titleCase } from "./Workspace";
import { Brand } from "./Brand";

interface NavigationItem {
  label: string;
  to: string;
  permissions?: Permission[];
}

const navigation: NavigationItem[] = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "My Day", to: "/my-day", permissions: ["sales:read_own", "sales:read_all"] },
  { label: "CRM", to: "/crm", permissions: ["sales:read_own", "sales:read_all"] },
  { label: "Pipeline", to: "/pipeline", permissions: ["sales:read_own", "sales:read_all"] },
  { label: "Leaderboard", to: "/leaderboard", permissions: ["dashboard:sales"] },
  { label: "Partners", to: "/partners", permissions: ["partner:read", "partner:read_assigned"] },
  { label: "Product Operations", to: "/product-operations", permissions: ["product:read"] },
  { label: "Company", to: "/company", permissions: ["objective:read", "task:read"] },
  { label: "Finance", to: "/finance", permissions: ["finance:read"] },
  { label: "Admin", to: "/admin", permissions: ["staff:manage"] },
];

interface AppShellProps extends PropsWithChildren {
  user: MeResponse;
  onSignOut: () => void;
}

export function AppShell({ user, onSignOut, children }: AppShellProps) {
  const initials = user.display_name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
  const permittedNavigation = navigation.filter((item) => !item.permissions || item.permissions.some((permission) => user.permissions.includes(permission)));

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
      <div className="app-main">
        <GlobalBar user={user} />
        <main className="app-content">{children}</main>
      </div>
    </div>
  );
}

function GlobalBar({ user }: { user: MeResponse }) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [q, setQ] = useState("");
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const notifications = useQuery({ queryKey: ["notifications"], queryFn: listNotifications, enabled: notificationsOpen });
  const search = useQuery({ queryKey: ["search", q.trim()], queryFn: () => searchEverything(q), enabled: searchOpen && q.trim().length >= 2 });
  const markRead = useMutation({ mutationFn: readNotification, onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["notifications"] }) });
  const notificationItems = notifications.data?.items ?? [];
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setSearchOpen(true); }
      if (event.key === "Escape") { setSearchOpen(false); setNotificationsOpen(false); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  useEffect(() => { setSearchOpen(false); setNotificationsOpen(false); }, [location.pathname]);
  const go = (href: string | null | undefined, type: string) => { navigate(href ?? ({ account: "/crm", contact: "/crm?view=contacts", partner: "/partners", opportunity: "/pipeline", task: "/company" }[type] ?? "/dashboard")); setSearchOpen(false); };
  return <header className="global-bar">
    <button className="global-search-trigger" type="button" onClick={() => setSearchOpen(true)}><span>⌕</span><span>Search SIFT OS</span><kbd>⌘ K</kbd></button>
    <div className="global-actions"><button className="notification-button" aria-label="Notifications" type="button" onClick={() => setNotificationsOpen((value) => !value)}>♢{notificationItems.some((item) => !item.read_at) && <i />}</button><span className="global-role">{titleCase(user.roles[0])}</span></div>
    {notificationsOpen && <div className="popover notifications-popover"><header><strong>Notifications</strong><span>{notifications.data?.unread ?? 0} unread</span></header>{notifications.isLoading && <p>Loading notifications…</p>}{notifications.isError && <p role="alert">{notifications.error.message}</p>}{notifications.data && !notificationItems.length && <p>You're all caught up.</p>}{notificationItems.map((item) => <button key={item.id} type="button" className={item.read_at ? "read" : ""} onClick={() => { if (!item.read_at) markRead.mutate(item.id); go(item.href, item.entity_type ?? item.event_type ?? ""); }}><span>{item.title}</span><small>{item.body}</small><time>{formatDate(item.created_at, true)}</time></button>)}</div>}
    {searchOpen && <div className="command-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setSearchOpen(false); }}><section className="command-palette" role="dialog" aria-modal="true" aria-label="Global search"><label><span>⌕</span><input autoFocus aria-label="Global search" value={q} onChange={(event) => setQ(event.target.value)} placeholder="Search accounts, contacts, partners, deals and tasks…"/><kbd>ESC</kbd></label><div>{q.trim().length < 2 && <p>Type at least two characters to search live records.</p>}{search.isFetching && <p>Searching…</p>}{search.isError && <p role="alert">{search.error.message}</p>}{search.data && !itemsOf(search.data).length && <p>No matching records.</p>}{itemsOf(search.data).map((item) => <button key={`${item.type}-${item.id}`} type="button" onClick={() => go(item.href, item.type)}><span className="result-type">{titleCase(item.type)}</span><strong>{item.label}</strong><small>{item.detail}</small><span>↗</span></button>)}</div></section></div>}
  </header>;
}
