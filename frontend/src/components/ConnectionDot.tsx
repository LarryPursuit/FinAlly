"use client";

import type { ConnectionStatus } from "@/lib/types";

const statusColors: Record<ConnectionStatus, string> = {
  connected: "bg-gain",
  connecting: "bg-accent-yellow",
  disconnected: "bg-loss",
};

const statusLabels: Record<ConnectionStatus, string> = {
  connected: "Live",
  connecting: "Connecting",
  disconnected: "Disconnected",
};

export function ConnectionDot({ status }: { status: ConnectionStatus }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-terminal-muted">
      <span
        className={`h-2 w-2 rounded-full ${statusColors[status]} ${
          status === "connected" ? "animate-pulse" : ""
        }`}
      />
      {statusLabels[status]}
    </span>
  );
}
