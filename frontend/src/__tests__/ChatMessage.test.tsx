import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatMessage } from "@/components/ChatMessage";
import type { ChatMessage as ChatMessageType } from "@/lib/types";

describe("ChatMessage", () => {
  it("renders user message content", () => {
    const msg: ChatMessageType = {
      id: "user-1",
      role: "user",
      content: "Buy 5 shares of AAPL",
    };
    render(<ChatMessage msg={msg} />);
    expect(screen.getByText("Buy 5 shares of AAPL")).toBeInTheDocument();
  });

  it("renders assistant message content", () => {
    const msg: ChatMessageType = {
      id: "assistant-1",
      role: "assistant",
      content: "I have purchased 5 shares of AAPL.",
    };
    render(<ChatMessage msg={msg} />);
    expect(
      screen.getByText("I have purchased 5 shares of AAPL.")
    ).toBeInTheDocument();
  });

  it("renders trade actions for assistant messages", () => {
    const msg: ChatMessageType = {
      id: "assistant-1",
      role: "assistant",
      content: "Done.",
      trades: [
        { ticker: "AAPL", side: "buy", quantity: 5, price: 190.25, success: true },
      ],
    };
    render(<ChatMessage msg={msg} />);
    expect(screen.getByText(/BUY 5 AAPL/)).toBeInTheDocument();
  });

  it("does not render ChatActions for user messages", () => {
    const msg: ChatMessageType = {
      id: "user-1",
      role: "user",
      content: "Hello",
      trades: [
        { ticker: "AAPL", side: "buy", quantity: 5, price: 190, success: true },
      ],
    };
    render(<ChatMessage msg={msg} />);
    // ChatActions is only rendered for non-user messages
    expect(screen.queryByText(/BUY/)).not.toBeInTheDocument();
  });
});
