"use client";

import type { ReactNode } from "react";
import { PriceProvider } from "@/contexts/PriceContext";
import { PortfolioProvider } from "@/contexts/PortfolioContext";
import { WatchlistProvider } from "@/contexts/WatchlistContext";
import { ChatProvider } from "@/contexts/ChatContext";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <PriceProvider>
      <PortfolioProvider>
        <WatchlistProvider>
          <ChatProvider>{children}</ChatProvider>
        </WatchlistProvider>
      </PortfolioProvider>
    </PriceProvider>
  );
}
