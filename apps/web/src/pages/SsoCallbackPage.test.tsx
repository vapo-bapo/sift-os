import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { exchangeSso } from "../features/auth/api";
import { SsoCallbackPage } from "./SsoCallbackPage";

vi.mock("../features/auth/api", () => ({ exchangeSso: vi.fn() }));

const mockedExchangeSso = vi.mocked(exchangeSso);

describe("SsoCallbackPage", () => {
  beforeEach(() => {
    mockedExchangeSso.mockReset();
    window.localStorage.clear();
    window.history.replaceState({}, "", "/auth/callback?sso_ticket=secret&sso_audience=sift-os");
  });

  it("exchanges the ticket without storing it and removes it from the URL", async () => {
    mockedExchangeSso.mockResolvedValue(undefined);

    render(<MemoryRouter><SsoCallbackPage /></MemoryRouter>);

    await waitFor(() => expect(mockedExchangeSso).toHaveBeenCalledWith("secret"));
    expect(window.localStorage).toHaveLength(0);
    expect(window.location.search).toBe("");
  });

  it("rejects a callback meant for another audience", async () => {
    window.history.replaceState({}, "", "/auth/callback?sso_ticket=secret&sso_audience=other");

    render(<MemoryRouter><SsoCallbackPage /></MemoryRouter>);

    expect(await screen.findByText(/not intended for SIFT OS/i)).toBeTruthy();
    expect(mockedExchangeSso).not.toHaveBeenCalled();
  });
});
