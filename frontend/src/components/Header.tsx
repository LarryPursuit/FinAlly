"use client";

import { usePrices } from "@/contexts/PriceContext";
import { usePortfolio } from "@/contexts/PortfolioContext";
import { ConnectionDot } from "./ConnectionDot";
import { formatCurrency } from "@/lib/format";

export function Header() {
  const { connectionStatus } = usePrices();
  const { portfolio } = usePortfolio();

  return (
    <header className="flex items-center justify-between px-4 py-2 border-b border-terminal-border bg-terminal-surface">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-mono font-bold text-accent-yellow tracking-wide">
          FinAlly
        </h1>
        <ConnectionDot status={connectionStatus} />
      </div>

      {portfolio && (
        <div className="flex items-center gap-6 text-sm font-mono">
          <div>
            <span className="text-terminal-muted mr-1">Portfolio</span>
            <span className="text-terminal-text font-medium">
              {formatCurrency(portfolio.total_value)}
            </span>
          </div>
          <div>
            <span className="text-terminal-muted mr-1">Cash</span>
            <span className="text-terminal-text font-medium">
              {formatCurrency(portfolio.cash_balance)}
            </span>
          </div>
        </div>
      )}
    </header>
  );
}
