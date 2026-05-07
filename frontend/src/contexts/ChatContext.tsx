"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { api } from "@/lib/api";
import { usePortfolio } from "./PortfolioContext";
import { useWatchlist } from "./WatchlistContext";
import type { ChatMessage } from "@/lib/types";

interface ChatContextValue {
  messages: ChatMessage[];
  sending: boolean;
  sendMessage: (text: string) => Promise<void>;
}

const ChatCtx = createContext<ChatContextValue | null>(null);

let msgCounter = 0;

export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const { refetch: refetchPortfolio } = usePortfolio();
  const { refetch: refetchWatchlist } = useWatchlist();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const history = await api.getChatHistory();
        if (cancelled) return;
        const restored: ChatMessage[] = history.messages.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
        }));
        setMessages(restored);
      } catch {
        // history endpoint may not exist yet; chat starts empty
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      const userMsg: ChatMessage = {
        id: `user-${++msgCounter}`,
        role: "user",
        content: text,
      };
      setMessages((prev) => [...prev, userMsg]);
      setSending(true);

      try {
        const res = await api.sendMessage(text);

        const assistantMsg: ChatMessage = {
          id: `assistant-${++msgCounter}`,
          role: "assistant",
          content: res.message,
          trades: res.trades,
          watchlist_changes: res.watchlist_changes,
          errors: res.errors,
        };
        setMessages((prev) => [...prev, assistantMsg]);

        // Refetch if trades or watchlist changes occurred
        const hasTrades = res.trades.length > 0;
        const hasWatchlistChanges = res.watchlist_changes.length > 0;
        if (hasTrades) await refetchPortfolio();
        if (hasWatchlistChanges) await refetchWatchlist();
      } catch (err) {
        const errorMsg: ChatMessage = {
          id: `error-${++msgCounter}`,
          role: "assistant",
          content:
            err instanceof Error
              ? `Error: ${err.message}`
              : "Something went wrong.",
          errors: [err instanceof Error ? err.message : "Unknown error"],
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setSending(false);
      }
    },
    [refetchPortfolio, refetchWatchlist]
  );

  return (
    <ChatCtx.Provider value={{ messages, sending, sendMessage }}>
      {children}
    </ChatCtx.Provider>
  );
}

export function useChat() {
  const ctx = useContext(ChatCtx);
  if (!ctx) throw new Error("useChat must be used within ChatProvider");
  return ctx;
}
