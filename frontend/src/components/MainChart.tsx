"use client";

import { useEffect, useRef } from "react";
import { createChart, LineSeries, type IChartApi, type ISeriesApi, type LineData } from "lightweight-charts";
import { usePrices } from "@/contexts/PriceContext";

export function MainChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const { selectedTicker, priceHistory } = usePrices();

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
      crosshair: {
        vertLine: { color: "#484f58", labelBackgroundColor: "#30363d" },
        horzLine: { color: "#484f58", labelBackgroundColor: "#30363d" },
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

    const series = chart.addSeries(LineSeries, {
      color: "#209dd7",
      lineWidth: 2,
      crosshairMarkerRadius: 4,
      crosshairMarkerBorderColor: "#209dd7",
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

  // Update data when ticker or history changes
  useEffect(() => {
    if (!seriesRef.current || !selectedTicker) return;

    const history = priceHistory[selectedTicker] ?? [];
    const lineData: LineData[] = history.map((p) => ({
      time: p.time as LineData["time"],
      value: p.price,
    }));

    seriesRef.current.setData(lineData);

    if (lineData.length > 0) {
      chartRef.current?.timeScale().fitContent();
    }
  }, [selectedTicker, priceHistory]);

  if (!selectedTicker) {
    return (
      <div className="flex items-center justify-center h-full text-terminal-muted text-sm font-mono">
        Select a ticker to view chart
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-terminal-border">
        <h2 className="text-xs font-mono uppercase tracking-wider text-terminal-muted">
          Chart — <span className="text-accent-blue">{selectedTicker}</span>
        </h2>
      </div>
      <div ref={containerRef} className="flex-1 min-h-0" />
    </div>
  );
}
