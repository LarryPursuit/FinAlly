"use client";

import { usePortfolio } from "@/contexts/PortfolioContext";
import { formatCurrency, formatPercent, formatPrice, formatQuantity } from "@/lib/format";

export function PositionsTable() {
  const { portfolio } = usePortfolio();
  const positions = portfolio?.positions ?? [];

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-terminal-border">
        <h2 className="text-xs font-mono uppercase tracking-wider text-terminal-muted">
          Positions
        </h2>
      </div>

      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="text-terminal-muted border-b border-terminal-border">
              <th className="text-left px-3 py-1.5 font-normal">Ticker</th>
              <th className="text-right px-3 py-1.5 font-normal">Qty</th>
              <th className="text-right px-3 py-1.5 font-normal">Avg Cost</th>
              <th className="text-right px-3 py-1.5 font-normal">Price</th>
              <th className="text-right px-3 py-1.5 font-normal">Value</th>
              <th className="text-right px-3 py-1.5 font-normal">P&L</th>
              <th className="text-right px-3 py-1.5 font-normal">%</th>
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 ? (
              <tr>
                <td
                  colSpan={7}
                  className="text-center text-terminal-muted py-6"
                >
                  No positions yet
                </td>
              </tr>
            ) : (
              positions.map((pos) => (
                <tr
                  key={pos.ticker}
                  className="border-b border-terminal-border/50 hover:bg-terminal-surface/50"
                >
                  <td className="px-3 py-1.5 text-accent-blue font-medium">
                    {pos.ticker}
                  </td>
                  <td className="text-right px-3 py-1.5">
                    {formatQuantity(pos.quantity)}
                  </td>
                  <td className="text-right px-3 py-1.5">
                    {formatPrice(pos.avg_cost)}
                  </td>
                  <td className="text-right px-3 py-1.5">
                    {formatPrice(pos.current_price)}
                  </td>
                  <td className="text-right px-3 py-1.5">
                    {formatCurrency(pos.market_value)}
                  </td>
                  <td
                    className={`text-right px-3 py-1.5 ${
                      pos.unrealized_pnl >= 0 ? "text-gain" : "text-loss"
                    }`}
                  >
                    {formatCurrency(pos.unrealized_pnl)}
                  </td>
                  <td
                    className={`text-right px-3 py-1.5 ${
                      pos.unrealized_pnl_pct >= 0 ? "text-gain" : "text-loss"
                    }`}
                  >
                    {formatPercent(pos.unrealized_pnl_pct)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
