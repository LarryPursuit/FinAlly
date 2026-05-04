import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { PositionsTable } from "@/components/PositionsTable";
import type { PortfolioResponse } from "@/lib/types";

const mockPortfolio: PortfolioResponse = {
  cash_balance: 8500.5,
  total_value: 12350.75,
  positions: [
    {
      ticker: "AAPL",
      quantity: 10,
      avg_cost: 185.5,
      current_price: 190.25,
      market_value: 1902.5,
      unrealized_pnl: 47.5,
      unrealized_pnl_pct: 2.56,
    },
    {
      ticker: "TSLA",
      quantity: 5,
      avg_cost: 250.0,
      current_price: 240.0,
      market_value: 1200.0,
      unrealized_pnl: -50.0,
      unrealized_pnl_pct: -4.0,
    },
  ],
};

vi.mock("@/contexts/PortfolioContext", () => ({
  usePortfolio: () => ({
    portfolio: mockPortfolio,
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

describe("PositionsTable", () => {
  it("renders the Positions heading", () => {
    render(<PositionsTable />);
    expect(screen.getByText("Positions")).toBeInTheDocument();
  });

  it("renders all column headers", () => {
    render(<PositionsTable />);
    expect(screen.getByText("Ticker")).toBeInTheDocument();
    expect(screen.getByText("Qty")).toBeInTheDocument();
    expect(screen.getByText("Avg Cost")).toBeInTheDocument();
    expect(screen.getByText("Price")).toBeInTheDocument();
    expect(screen.getByText("Value")).toBeInTheDocument();
    expect(screen.getByText("P&L")).toBeInTheDocument();
    expect(screen.getByText("%")).toBeInTheDocument();
  });

  it("renders position ticker symbols", () => {
    render(<PositionsTable />);
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("TSLA")).toBeInTheDocument();
  });

  it("renders formatted values for positions", () => {
    render(<PositionsTable />);
    // AAPL qty=10 (integer)
    expect(screen.getByText("10")).toBeInTheDocument();
    // AAPL avg_cost=185.50
    expect(screen.getByText("185.50")).toBeInTheDocument();
    // AAPL current_price=190.25
    expect(screen.getByText("190.25")).toBeInTheDocument();
    // AAPL market_value=$1,902.50
    expect(screen.getByText("$1,902.50")).toBeInTheDocument();
    // AAPL P&L=$47.50
    expect(screen.getByText("$47.50")).toBeInTheDocument();
  });

  it("renders negative P&L for losing positions", () => {
    render(<PositionsTable />);
    expect(screen.getByText("-$50.00")).toBeInTheDocument();
  });
});
