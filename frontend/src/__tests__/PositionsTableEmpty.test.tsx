import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { PositionsTable } from "@/components/PositionsTable";

vi.mock("@/contexts/PortfolioContext", () => ({
  usePortfolio: () => ({
    portfolio: {
      cash_balance: 10000,
      total_value: 10000,
      positions: [],
    },
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

describe("PositionsTable (empty)", () => {
  it("renders 'No positions yet' when portfolio has no positions", () => {
    render(<PositionsTable />);
    expect(screen.getByText("No positions yet")).toBeInTheDocument();
  });
});
