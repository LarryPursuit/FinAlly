"use client";

import { Header } from "@/components/Header";
import { Watchlist } from "@/components/Watchlist";
import { MainChart } from "@/components/MainChart";
import { PortfolioHeatmap } from "@/components/PortfolioHeatmap";
import { PnlChart } from "@/components/PnlChart";
import { PositionsTable } from "@/components/PositionsTable";
import { TradeBar } from "@/components/TradeBar";
import { ChatPanel } from "@/components/ChatPanel";

export default function Home() {
  return (
    <div className="h-screen flex flex-col bg-terminal-bg">
      <Header />

      <div className="flex-1 flex min-h-0">
        {/* Main grid area */}
        <div className="flex-1 grid grid-cols-[280px_1fr_280px] grid-rows-[1fr_240px] min-h-0 gap-px bg-terminal-border">
          {/* Row 1 */}
          <div className="bg-terminal-bg overflow-hidden">
            <Watchlist />
          </div>
          <div className="bg-terminal-bg overflow-hidden">
            <MainChart />
          </div>
          <div className="bg-terminal-bg overflow-hidden">
            <PortfolioHeatmap />
          </div>

          {/* Row 2 */}
          <div className="bg-terminal-bg overflow-hidden">
            <PositionsTable />
          </div>
          <div className="bg-terminal-bg overflow-hidden">
            <PnlChart />
          </div>
          <div className="bg-terminal-bg overflow-hidden">
            <TradeBar />
          </div>
        </div>

        {/* Chat sidebar */}
        <ChatPanel />
      </div>
    </div>
  );
}
