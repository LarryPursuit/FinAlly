import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TradeBar } from "@/components/TradeBar";

const mockRefetch = vi.fn();
const mockExecuteTrade = vi.fn();

vi.mock("@/contexts/PriceContext", () => ({
  usePrices: () => ({
    selectedTicker: "AAPL",
    prices: {},
    priceHistory: {},
    connectionStatus: "connected" as const,
    selectTicker: vi.fn(),
  }),
}));

vi.mock("@/contexts/PortfolioContext", () => ({
  usePortfolio: () => ({
    portfolio: null,
    loading: false,
    error: null,
    refetch: mockRefetch,
  }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    executeTrade: (...args: unknown[]) => mockExecuteTrade(...args),
  },
  ApiRequestError: class ApiRequestError extends Error {
    code: string;
    status: number;
    constructor(message: string, code: string, status: number) {
      super(message);
      this.name = "ApiRequestError";
      this.code = code;
      this.status = status;
    }
  },
}));

describe("TradeBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Buy and Sell buttons", () => {
    render(<TradeBar />);
    expect(screen.getByText("Buy")).toBeInTheDocument();
    expect(screen.getByText("Sell")).toBeInTheDocument();
  });

  it("renders ticker and quantity inputs", () => {
    render(<TradeBar />);
    expect(screen.getByPlaceholderText("AAPL")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Qty")).toBeInTheDocument();
  });

  it("shows error when submitting without quantity", async () => {
    render(<TradeBar />);
    fireEvent.click(screen.getByText("Buy"));
    expect(
      await screen.findByText("Enter a valid ticker and quantity")
    ).toBeInTheDocument();
  });

  it("executes a buy trade successfully", async () => {
    const user = userEvent.setup();
    mockExecuteTrade.mockResolvedValueOnce({
      success: true,
      trade: { id: "1", ticker: "AAPL", side: "buy", quantity: 10, price: 190.25, executed_at: "" },
      new_cash_balance: 8097.5,
      new_position: { ticker: "AAPL", quantity: 10, avg_cost: 190.25 },
    });

    render(<TradeBar />);

    const qtyInput = screen.getByPlaceholderText("Qty");
    await user.type(qtyInput, "10");
    await user.click(screen.getByText("Buy"));

    await waitFor(() => {
      expect(mockExecuteTrade).toHaveBeenCalledWith({
        ticker: "AAPL",
        quantity: 10,
        side: "buy",
      });
    });

    expect(await screen.findByText(/Bought 10 AAPL/)).toBeInTheDocument();
    expect(mockRefetch).toHaveBeenCalled();
  });

  it("shows error on failed trade", async () => {
    const user = userEvent.setup();
    mockExecuteTrade.mockRejectedValueOnce(new Error("Insufficient cash"));

    render(<TradeBar />);

    const qtyInput = screen.getByPlaceholderText("Qty");
    await user.type(qtyInput, "5");
    await user.click(screen.getByText("Buy"));

    expect(await screen.findByText("Trade failed")).toBeInTheDocument();
  });

  it("only allows digits in quantity field", async () => {
    const user = userEvent.setup();
    render(<TradeBar />);

    const qtyInput = screen.getByPlaceholderText("Qty") as HTMLInputElement;
    await user.type(qtyInput, "abc123");
    expect(qtyInput.value).toBe("123");
  });
});
