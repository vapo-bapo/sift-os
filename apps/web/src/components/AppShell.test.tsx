import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AppShell } from "./AppShell";
import type { MeResponse } from "../features/auth/types";

function me(overrides: Partial<MeResponse>): MeResponse {
  return {
    id: "staff-1",
    display_name: "Coding Staff",
    department: "coding",
    roles: ["coding"],
    permissions: ["product:read"],
    ...overrides,
  };
}

function renderShell(user: MeResponse) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}><MemoryRouter>
      <AppShell user={user} onSignOut={() => undefined}><p>Content</p></AppShell>
    </MemoryRouter></QueryClientProvider>,
  );
}

describe("AppShell", () => {
  it("does not render Finance for coding-only staff", () => {
    renderShell(me({ roles: ["coding"], permissions: ["product:read"] }));

    expect(screen.getByRole("link", { name: "Product Operations" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Finance" })).toBeNull();
  });

  it("renders finance navigation when the permission is granted", () => {
    renderShell(me({ permissions: ["finance:read"] }));

    expect(screen.getByRole("link", { name: "Finance" })).toBeTruthy();
  });

  it("shows the commercial workspace without exposing administration to sales", () => {
    renderShell(me({
      roles: ["sales"],
      department: "sales",
      permissions: ["dashboard:sales", "sales:read_own", "sales:write_own", "partner:read_assigned", "task:read"],
    }));

    expect(screen.getByRole("link", { name: "My Day" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "CRM" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Pipeline" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Partners" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Admin" })).toBeNull();
  });

  it("shows company governance and admin only with matching permissions", () => {
    renderShell(me({
      roles: ["ceo", "admin"],
      permissions: ["dashboard:company", "objective:read", "staff:manage"],
    }));

    expect(screen.getByRole("link", { name: "Company" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Admin" })).toBeTruthy();
  });
});
