import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "./AuthProvider";
import { getMe, logout } from "./api";

vi.mock("./api", () => ({
  getMe: vi.fn(),
  logout: vi.fn(),
}));

const mockedGetMe = vi.mocked(getMe);
const mockedLogout = vi.mocked(logout);

function AuthStatus() {
  const { status, user, signOut } = useAuth();
  return (
    <>
      <p>{status}</p>
      <p>{user?.display_name ?? "No user"}</p>
      <button type="button" onClick={() => void signOut()}>Sign out</button>
    </>
  );
}

describe("AuthProvider", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    mockedGetMe.mockReset();
    mockedLogout.mockReset();
  });

  it("loads the authenticated staff identity", async () => {
    mockedGetMe.mockResolvedValue({
      id: "staff-1",
      display_name: "Coding Staff",
      department: "coding",
      roles: ["coding"],
      permissions: ["product:read"],
    });

    render(<AuthProvider><AuthStatus /></AuthProvider>);

    expect(screen.getByText("loading")).toBeTruthy();
    expect(await screen.findByText("authenticated")).toBeTruthy();
    expect(screen.getByText("Coding Staff")).toBeTruthy();
  });

  it("returns to anonymous after signing out", async () => {
    mockedGetMe.mockResolvedValue({
      id: "staff-1",
      display_name: "Coding Staff",
      department: "coding",
      roles: ["coding"],
      permissions: ["product:read"],
    });
    mockedLogout.mockResolvedValue(undefined);

    render(<AuthProvider><AuthStatus /></AuthProvider>);
    await screen.findByText("authenticated");
    screen.getByRole("button", { name: "Sign out" }).click();

    await waitFor(() => expect(mockedLogout).toHaveBeenCalledOnce());
    expect(screen.getByText("anonymous")).toBeTruthy();
    expect(screen.getByText("No user")).toBeTruthy();
  });
});
