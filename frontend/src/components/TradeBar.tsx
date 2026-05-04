"use client";

import { useState } from "react";
import { usePrices } from "@/contexts/PriceContext";
import { usePortfolio } from "@/contexts/PortfolioContext";
import { api, ApiRequestError } from "@/lib/api";

export function TradeBar() {
  const { selectedTicker } = usePrices();
  const { refetch } = usePortfolio();
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [status, setStatus] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const effectiveTicker = ticker.trim().toUpperCase() || selectedTicker || "";

  const executeTrade = async (side: "buy" | "sell") => {
    const qty = parseInt(quantity, 10);
    if (!effectiveTicker || isNaN(qty) || qty <= 0) {
      setStatus({ type: "error", message: "Enter a valid ticker and quantity" });
      return;
    }

    setSubmitting(true);
    setStatus(null);

    try {
      const res = await api.executeTrade({
        ticker: effectiveTicker,
        quantity: qty,
        side,
      });
      setStatus({
        type: "success",
        message: `${side === "buy" ? "Bought" : "Sold"} ${res.trade.quantity} ${res.trade.ticker} @ $${res.trade.price.toFixed(2)}`,
      });
      setQuantity("");
      await refetch();
    } catch (err) {
      const message =
        err instanceof ApiRequestError
          ? err.message
          : "Trade failed";
      setStatus({ type: "error", message });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-2 p-3">
      <div className="flex items-center gap-2">
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder={selectedTicker || "Ticker"}
          className="w-20 bg-terminal-bg border border-terminal-border rounded px-2 py-1.5 text-xs font-mono text-terminal-text placeholder:text-terminal-muted focus:outline-none focus:border-accent-blue uppercase"
        />
        <input
          value={quantity}
          onChange={(e) => setQuantity(e.target.value.replace(/\D/g, ""))}
          placeholder="Qty"
          className="w-16 bg-terminal-bg border border-terminal-border rounded px-2 py-1.5 text-xs font-mono text-terminal-text placeholder:text-terminal-muted focus:outline-none focus:border-accent-blue"
        />
        <button
          onClick={() => executeTrade("buy")}
          disabled={submitting}
          className="px-3 py-1.5 text-xs font-mono font-medium bg-gain/20 text-gain rounded hover:bg-gain/30 disabled:opacity-40 transition-colors"
        >
          Buy
        </button>
        <button
          onClick={() => executeTrade("sell")}
          disabled={submitting}
          className="px-3 py-1.5 text-xs font-mono font-medium bg-loss/20 text-loss rounded hover:bg-loss/30 disabled:opacity-40 transition-colors"
        >
          Sell
        </button>
      </div>
      {status && (
        <p
          className={`text-xs font-mono ${
            status.type === "success" ? "text-gain" : "text-loss"
          }`}
        >
          {status.message}
        </p>
      )}
    </div>
  );
}
