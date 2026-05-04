"use client";

import { useState } from "react";
import { usePrices } from "@/contexts/PriceContext";
import { useWatchlist } from "@/contexts/WatchlistContext";
import { WatchlistRow } from "./WatchlistRow";

export function Watchlist() {
  const { tickers, addTicker, removeTicker } = useWatchlist();
  const { selectedTicker, selectTicker } = usePrices();
  const [input, setInput] = useState("");
  const [adding, setAdding] = useState(false);

  const handleAdd = async () => {
    const ticker = input.trim().toUpperCase();
    if (!ticker) return;
    setAdding(true);
    await addTicker(ticker);
    setInput("");
    setAdding(false);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-terminal-border">
        <h2 className="text-xs font-mono uppercase tracking-wider text-terminal-muted">
          Watchlist
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto">
        {tickers.map((t) => (
          <div key={t.ticker} className="group relative">
            <WatchlistRow
              ticker={t.ticker}
              onSelect={selectTicker}
              selected={selectedTicker === t.ticker}
            />
            <button
              onClick={() => removeTicker(t.ticker)}
              className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 text-terminal-muted hover:text-loss text-xs px-1 transition-opacity"
              title={`Remove ${t.ticker}`}
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      <div className="flex gap-1 p-2 border-t border-terminal-border">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="Add ticker..."
          className="flex-1 bg-terminal-bg border border-terminal-border rounded px-2 py-1 text-xs font-mono text-terminal-text placeholder:text-terminal-muted focus:outline-none focus:border-accent-blue"
          disabled={adding}
        />
        <button
          onClick={handleAdd}
          disabled={adding || !input.trim()}
          className="px-2 py-1 text-xs font-mono bg-accent-blue/20 text-accent-blue rounded hover:bg-accent-blue/30 disabled:opacity-40 transition-colors"
        >
          Add
        </button>
      </div>
    </div>
  );
}
