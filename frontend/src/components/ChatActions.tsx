"use client";

import type { ChatTradeResult, ChatWatchlistChange } from "@/lib/types";

interface ChatActionsProps {
  trades?: ChatTradeResult[];
  watchlist_changes?: ChatWatchlistChange[];
}

export function ChatActions({ trades, watchlist_changes }: ChatActionsProps) {
  const hasTrades = trades && trades.length > 0;
  const hasChanges = watchlist_changes && watchlist_changes.length > 0;

  if (!hasTrades && !hasChanges) return null;

  return (
    <div className="flex flex-wrap gap-1.5 mt-1.5">
      {trades?.map((t, i) => (
        <span
          key={`trade-${i}`}
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono ${
            t.success
              ? t.side === "buy"
                ? "bg-gain/15 text-gain"
                : "bg-loss/15 text-loss"
              : "bg-loss/15 text-loss line-through"
          }`}
        >
          {t.side.toUpperCase()} {t.quantity} {t.ticker}
          {t.price != null && t.success && ` @$${t.price.toFixed(2)}`}
        </span>
      ))}
      {watchlist_changes?.map((w, i) => (
        <span
          key={`wl-${i}`}
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono ${
            w.success
              ? "bg-accent-blue/15 text-accent-blue"
              : "bg-loss/15 text-loss line-through"
          }`}
        >
          {w.action === "add" ? "+" : "−"} {w.ticker}
        </span>
      ))}
    </div>
  );
}
