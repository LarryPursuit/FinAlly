"use client";

import { usePrices } from "@/contexts/PriceContext";
import { usePriceFlash } from "@/hooks/usePriceFlash";
import { Sparkline } from "./Sparkline";
import { formatPrice, formatPercent } from "@/lib/format";

interface WatchlistRowProps {
  ticker: string;
  onSelect: (ticker: string) => void;
  selected: boolean;
}

export function WatchlistRow({ ticker, onSelect, selected }: WatchlistRowProps) {
  const { prices, priceHistory } = usePrices();
  const priceData = prices[ticker];
  const history = priceHistory[ticker] ?? [];
  const flashClass = usePriceFlash(priceData?.price);

  const price = priceData?.price;
  const changePct = priceData?.change_percent;
  const direction = priceData?.direction;

  return (
    <button
      onClick={() => onSelect(ticker)}
      className={`w-full flex items-center gap-3 px-3 py-2 text-left font-mono text-sm transition-colors rounded ${flashClass} ${
        selected
          ? "bg-terminal-border/50"
          : "hover:bg-terminal-surface"
      }`}
    >
      <span className="w-14 font-medium text-accent-blue">{ticker}</span>

      <span className="w-16 text-right">
        {price != null ? formatPrice(price) : "—"}
      </span>

      <span
        className={`w-16 text-right text-xs ${
          direction === "up"
            ? "text-gain"
            : direction === "down"
            ? "text-loss"
            : "text-terminal-muted"
        }`}
      >
        {changePct != null ? formatPercent(changePct) : "—"}
      </span>

      <span className="ml-auto">
        <Sparkline data={history.slice(-60)} />
      </span>
    </button>
  );
}
