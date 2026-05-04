import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WatchlistRow } from "@/components/WatchlistRow";

vi.mock("@/contexts/PriceContext", () => ({
  usePrices: () => ({
    prices: {
      AAPL: {
        ticker: "AAPL",
        price: 190.25,
        previous_price: 189.5,
        timestamp: Date.now(),
        change: 0.75,
        change_percent: 0.4,
        direction: "up" as const,
      },
    },
    priceHistory: {
      AAPL: [
        { time: 1, price: 189 },
        { time: 2, price: 190 },
      ],
    },
    connectionStatus: "connected" as const,
    selectedTicker: null,
    selectTicker: vi.fn(),
  }),
}));

vi.mock("@/hooks/usePriceFlash", () => ({
  usePriceFlash: () => "",
}));

vi.mock("@/components/Sparkline", () => ({
  Sparkline: ({ data }: { data: unknown[] }) => (
    <div data-testid="sparkline">{data.length} points</div>
  ),
}));

describe("WatchlistRow", () => {
  it("renders the ticker symbol", () => {
    render(
      <WatchlistRow ticker="AAPL" onSelect={vi.fn()} selected={false} />
    );
    expect(screen.getByText("AAPL")).toBeInTheDocument();
  });

  it("renders the price", () => {
    render(
      <WatchlistRow ticker="AAPL" onSelect={vi.fn()} selected={false} />
    );
    expect(screen.getByText("190.25")).toBeInTheDocument();
  });

  it("renders the change percent", () => {
    render(
      <WatchlistRow ticker="AAPL" onSelect={vi.fn()} selected={false} />
    );
    expect(screen.getByText(/0\.40%/)).toBeInTheDocument();
  });

  it("renders sparkline with data", () => {
    render(
      <WatchlistRow ticker="AAPL" onSelect={vi.fn()} selected={false} />
    );
    expect(screen.getByTestId("sparkline")).toBeInTheDocument();
  });

  it("calls onSelect when clicked", () => {
    const onSelect = vi.fn();
    render(
      <WatchlistRow ticker="AAPL" onSelect={onSelect} selected={false} />
    );
    fireEvent.click(screen.getByRole("button"));
    expect(onSelect).toHaveBeenCalledWith("AAPL");
  });

  it("shows dash when no price data", () => {
    // Re-mock with empty prices for this test
    vi.doMock("@/contexts/PriceContext", () => ({
      usePrices: () => ({
        prices: {},
        priceHistory: {},
        connectionStatus: "connected" as const,
        selectedTicker: null,
        selectTicker: vi.fn(),
      }),
    }));
    // Since vi.doMock is lazy, we test with a ticker that has no data
    render(
      <WatchlistRow ticker="UNKNOWN" onSelect={vi.fn()} selected={false} />
    );
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });
});
