import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatActions } from "@/components/ChatActions";

describe("ChatActions", () => {
  it("renders nothing when no trades or watchlist changes", () => {
    const { container } = render(<ChatActions />);
    expect(container.firstChild).toBeNull();
  });

  it("renders successful buy trade", () => {
    render(
      <ChatActions
        trades={[
          { ticker: "AAPL", side: "buy", quantity: 10, price: 190.25, success: true },
        ]}
      />
    );
    expect(screen.getByText(/BUY 10 AAPL/)).toBeInTheDocument();
    expect(screen.getByText(/@\$190\.25/)).toBeInTheDocument();
  });

  it("renders failed trade with line-through styling", () => {
    render(
      <ChatActions
        trades={[
          { ticker: "TSLA", side: "sell", quantity: 5, success: false },
        ]}
      />
    );
    const el = screen.getByText(/SELL 5 TSLA/);
    expect(el.className).toContain("line-through");
  });

  it("renders watchlist add change", () => {
    render(
      <ChatActions
        watchlist_changes={[
          { ticker: "PYPL", action: "add", success: true },
        ]}
      />
    );
    expect(screen.getByText(/PYPL/)).toBeInTheDocument();
  });

  it("renders watchlist remove change", () => {
    render(
      <ChatActions
        watchlist_changes={[
          { ticker: "META", action: "remove", success: true },
        ]}
      />
    );
    expect(screen.getByText(/META/)).toBeInTheDocument();
  });

  it("renders both trades and watchlist changes", () => {
    render(
      <ChatActions
        trades={[
          { ticker: "AAPL", side: "buy", quantity: 1, price: 100, success: true },
        ]}
        watchlist_changes={[
          { ticker: "PYPL", action: "add", success: true },
        ]}
      />
    );
    expect(screen.getByText(/BUY 1 AAPL/)).toBeInTheDocument();
    expect(screen.getByText(/PYPL/)).toBeInTheDocument();
  });
});
