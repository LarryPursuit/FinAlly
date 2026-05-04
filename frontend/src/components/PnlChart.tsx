"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { createChart, AreaSeries, type IChartApi, type ISeriesApi, type AreaData } from "lightweight-charts";
import { api } from "@/lib/api";
import type { Snapshot } from "@/lib/types";

const POLL_INTERVAL = 30_000; // 30s

export function PnlChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);

  const fetchHistory = useCallback(async () => {
    try {
      const data = await api.getPortfolioHistory();
      setSnapshots(data.snapshots);
    } catch {
      // silently retry on next interval
    }
  }, []);

  // Poll for snapshots
  useEffect(() => {
    fetchHistory();
    const id = setInterval(fetchHistory, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [fetchHistory]);

  // Create chart
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: "#161b22" },
        textColor: "#8b949e",
        fontFamily: "var(--font-geist-mono), monospace",
      },
      grid: {
        vertLines: { color: "#30363d" },
        horzLines: { color: "#30363d" },
      },
      timeScale: {
        borderColor: "#30363d",
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: "#30363d",
      },
    });

    const series = chart.addSeries(AreaSeries, {
      lineColor: "#ecad0a",
      lineWidth: 2,
      topColor: "rgba(236, 173, 10, 0.3)",
      bottomColor: "rgba(236, 173, 10, 0.02)",
      crosshairMarkerRadius: 4,
      crosshairMarkerBorderColor: "#ecad0a",
      crosshairMarkerBackgroundColor: "#161b22",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const resizeObserver = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      chart.applyOptions({ width, height });
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Update data
  useEffect(() => {
    if (!seriesRef.current) return;

    const areaData: AreaData[] = snapshots.map((s) => ({
      time: (new Date(s.recorded_at).getTime() / 1000) as AreaData["time"],
      value: s.total_value,
    }));

    seriesRef.current.setData(areaData);

    if (areaData.length > 0) {
      chartRef.current?.timeScale().fitContent();
    }
  }, [snapshots]);

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-terminal-border">
        <h2 className="text-xs font-mono uppercase tracking-wider text-terminal-muted">
          Portfolio Value
        </h2>
      </div>
      <div ref={containerRef} className="flex-1 min-h-0" />
    </div>
  );
}
