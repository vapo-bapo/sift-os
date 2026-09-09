import { afterEach, describe, expect, it, vi } from "vitest";

import { listAccounts, moveOpportunity, searchEverything } from "./api";

describe("operational API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends CRM filters to the server instead of filtering in the browser", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], total: 0, page: 2, page_size: 25 }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await listAccounts({ q: "acme", owner_id: "staff-1", page: 2, page_size: 25 });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/accounts?owner_id=staff-1&page=2&page_size=25&search=acme",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("persists a kanban stage change through the dedicated transition endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "deal-1", stage: "qualified" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await moveOpportunity("deal-1", "qualified");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/opportunities/deal-1/stage",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ stage: "qualified" }) }),
    );
  });

  it("trims global search queries and caps the requested results", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [] }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await searchEverything("  auris  ");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/search?q=auris",
      expect.objectContaining({ credentials: "include" }),
    );
  });
});
