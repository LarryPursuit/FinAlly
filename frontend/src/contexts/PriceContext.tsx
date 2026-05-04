"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { useSSE } from "@/hooks/useSSE";
import type {
  PriceMap,
  PricePoint,
  ConnectionStatus,
} from "@/lib/types";

const MAX_HISTORY = 200;

interface PriceContextValue {
  prices: PriceMap;
  priceHistory: Record<string, PricePoint[]>;
  connectionStatus: ConnectionStatus;
  selectedTicker: string | null;
  selectTicker: (ticker: string) => void;
}

const PriceCtx = createContext<PriceContextValue | null>(null);

export function PriceProvider({ children }: { children: ReactNode }) {
  const [prices, setPrices] = useState<PriceMap>({});
  const [priceHistory, setPriceHistory] = useState<
    Record<string, PricePoint[]>
  >({});
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  const handleMessage = useCallback((data: PriceMap) => {
    setPrices((prev) => ({ ...prev, ...data }));

    setPriceHistory((prev) => {
      const next = { ...prev };
      for (const [ticker, update] of Object.entries(data)) {
        const point: PricePoint = { time: update.timestamp, price: update.price };
        const existing = next[ticker] ?? [];
        const updated = [...existing, point];
        next[ticker] =
          updated.length > MAX_HISTORY
            ? updated.slice(updated.length - MAX_HISTORY)
            : updated;
      }
      return next;
    });
  }, []);

  const connectionStatus = useSSE({
    url: "/api/stream/prices",
    onMessage: handleMessage,
  });

  return (
    <PriceCtx.Provider
      value={{
        prices,
        priceHistory,
        connectionStatus,
        selectedTicker,
        selectTicker: setSelectedTicker,
      }}
    >
      {children}
    </PriceCtx.Provider>
  );
}

export function usePrices() {
  const ctx = useContext(PriceCtx);
  if (!ctx) throw new Error("usePrices must be used within PriceProvider");
  return ctx;
}
