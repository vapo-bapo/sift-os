import { render, screen } from "@testing-library/react";
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
  render(
    <MemoryRouter>
      <AppShell user={user} onSignOut={() => undefined}><p>Content</p></AppShell>
    </MemoryRouter>,
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
});
