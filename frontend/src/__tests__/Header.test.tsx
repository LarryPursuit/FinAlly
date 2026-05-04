import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Header } from "@/components/Header";

// Mock the context hooks
vi.mock("@/contexts/PriceContext", () => ({
  usePrices: () => ({
    connectionStatus: "connected" as const,
    prices: {},
    priceHistory: {},
    selectedTicker: null,
    selectTicker: vi.fn(),
  }),
}));

vi.mock("@/contexts/PortfolioContext", () => ({
  usePortfolio: () => ({
    portfolio: {
      cash_balance: 8500.5,
      total_value: 12350.75,
      positions: [],
    },
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

describe("Header", () => {
  it("renders the FinAlly title", () => {
    render(<Header />);
    expect(screen.getByText("FinAlly")).toBeInTheDocument();
  });

  it("renders portfolio total value", () => {
    render(<Header />);
    expect(screen.getByText("$12,350.75")).toBeInTheDocument();
  });

  it("renders cash balance", () => {
    render(<Header />);
    expect(screen.getByText("$8,500.50")).toBeInTheDocument();
  });

  it("renders connection status", () => {
    render(<Header />);
    expect(screen.getByText("Live")).toBeInTheDocument();
  });

  it("renders Portfolio and Cash labels", () => {
    render(<Header />);
    expect(screen.getByText("Portfolio")).toBeInTheDocument();
    expect(screen.getByText("Cash")).toBeInTheDocument();
  });
});
