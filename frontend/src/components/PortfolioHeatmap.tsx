"use client";

import { usePortfolio } from "@/contexts/PortfolioContext";
import { formatPercent, formatCurrency } from "@/lib/format";

export function PortfolioHeatmap() {
  const { portfolio } = usePortfolio();
  const positions = portfolio?.positions ?? [];

  if (positions.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <div className="px-3 py-2 border-b border-terminal-border">
          <h2 className="text-xs font-mono uppercase tracking-wider text-terminal-muted">
            Heatmap
          </h2>
        </div>
        <div className="flex-1 flex items-center justify-center text-terminal-muted text-sm font-mono">
          No positions
        </div>
      </div>
    );
  }

  const totalMarketValue = positions.reduce((s, p) => s + p.market_value, 0);

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-terminal-border">
        <h2 className="text-xs font-mono uppercase tracking-wider text-terminal-muted">
          Heatmap
        </h2>
      </div>
      <div className="flex-1 flex flex-wrap content-start gap-1 p-2 overflow-hidden">
        {positions.map((pos) => {
          const weight = totalMarketValue > 0 ? pos.market_value / totalMarketValue : 0;
          const pnlPct = pos.unrealized_pnl_pct;
          const isGain = pnlPct >= 0;

          // Color intensity based on P&L magnitude (cap at 10%)
          const intensity = Math.min(Math.abs(pnlPct) / 10, 1);
          const bg = isGain
            ? `rgba(34, 197, 94, ${0.15 + intensity * 0.45})`
            : `rgba(239, 68, 68, ${0.15 + intensity * 0.45})`;

          return (
            <div
              key={pos.ticker}
              className="flex flex-col items-center justify-center rounded text-xs font-mono"
              style={{
                flexGrow: Math.max(weight * 100, 1),
                flexBasis: 0,
                minWidth: 60,
                minHeight: 48,
                backgroundColor: bg,
              }}
              title={`${pos.ticker}: ${formatCurrency(pos.market_value)} (${formatPercent(pnlPct)})`}
            >
              <span className="font-medium text-terminal-text">{pos.ticker}</span>
              <span className={isGain ? "text-gain" : "text-loss"}>
                {formatPercent(pnlPct)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
