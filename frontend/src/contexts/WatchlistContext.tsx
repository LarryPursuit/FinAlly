"use client";

import {
  createContext,
  useContext,
  useEffect,
  useCallback,
  useState,
  type ReactNode,
} from "react";
import { api } from "@/lib/api";
import type { WatchlistTicker } from "@/lib/types";

interface WatchlistContextValue {
  tickers: WatchlistTicker[];
  loading: boolean;
  error: string | null;
  addTicker: (ticker: string) => Promise<boolean>;
  removeTicker: (ticker: string) => Promise<boolean>;
  refetch: () => Promise<void>;
}

const WatchlistCtx = createContext<WatchlistContextValue | null>(null);

export function WatchlistProvider({ children }: { children: ReactNode }) {
  const [tickers, setTickers] = useState<WatchlistTicker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    try {
      setError(null);
      const data = await api.getWatchlist();
      setTickers(data.tickers);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load watchlist"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const addTicker = useCallback(
    async (ticker: string): Promise<boolean> => {
      try {
        await api.addTicker(ticker);
        await refetch();
        return true;
      } catch {
        return false;
      }
    },
    [refetch]
  );

  const removeTicker = useCallback(
    async (ticker: string): Promise<boolean> => {
      try {
        await api.removeTicker(ticker);
        await refetch();
        return true;
      } catch {
        return false;
      }
    },
    [refetch]
  );

  useEffect(() => {
    refetch();
  }, [refetch]);

  return (
    <WatchlistCtx.Provider
      value={{ tickers, loading, error, addTicker, removeTicker, refetch }}
    >
      {children}
    </WatchlistCtx.Provider>
  );
}

export function useWatchlist() {
  const ctx = useContext(WatchlistCtx);
  if (!ctx)
    throw new Error("useWatchlist must be used within WatchlistProvider");
  return ctx;
}
