import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApiRequestError } from "@/lib/api";

// We test ApiRequestError directly and the fetch-based API client behavior
describe("ApiRequestError", () => {
  it("creates an error with message, code, and status", () => {
    const err = new ApiRequestError("Insufficient cash", "INSUFFICIENT_CASH", 400);
    expect(err.message).toBe("Insufficient cash");
    expect(err.code).toBe("INSUFFICIENT_CASH");
    expect(err.status).toBe(400);
    expect(err.name).toBe("ApiRequestError");
  });

  it("is an instance of Error", () => {
    const err = new ApiRequestError("fail", "ERR", 500);
    expect(err).toBeInstanceOf(Error);
  });
});

describe("ApiClient", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.resetModules();
  });

  it("makes GET request for portfolio", async () => {
    const mockResponse = {
      cash_balance: 10000,
      total_value: 10000,
      positions: [],
    };
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    // Re-import to get a fresh client using our mocked fetch
    const { api } = await import("@/lib/api");
    const result = await api.getPortfolio();

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/portfolio",
      expect.objectContaining({
        headers: { "Content-Type": "application/json" },
      })
    );
    expect(result).toEqual(mockResponse);
  });

  it("makes POST request for trades", async () => {
    const mockResponse = {
      success: true,
      trade: { id: "1", ticker: "AAPL", side: "buy", quantity: 10, price: 190.25, executed_at: "" },
      new_cash_balance: 8097.5,
      new_position: { ticker: "AAPL", quantity: 10, avg_cost: 190.25 },
    };
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const { api } = await import("@/lib/api");
    const result = await api.executeTrade({
      ticker: "AAPL",
      quantity: 10,
      side: "buy",
    });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/portfolio/trade",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ ticker: "AAPL", quantity: 10, side: "buy" }),
      })
    );
    expect(result.success).toBe(true);
  });

  it("throws ApiRequestError on non-ok response", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: () =>
        Promise.resolve({ error: "Insufficient cash", code: "INSUFFICIENT_CASH" }),
    });

    const { api, ApiRequestError: AE } = await import("@/lib/api");

    await expect(
      api.executeTrade({ ticker: "AAPL", quantity: 10000, side: "buy" })
    ).rejects.toThrow(AE);
  });

  it("handles non-JSON error response gracefully", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error("not json")),
    });

    const { api } = await import("@/lib/api");

    await expect(
      api.getPortfolio()
    ).rejects.toThrow("Request failed: 500");
  });
});
