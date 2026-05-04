import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConnectionDot } from "@/components/ConnectionDot";

describe("ConnectionDot", () => {
  it("renders 'Live' text when connected", () => {
    render(<ConnectionDot status="connected" />);
    expect(screen.getByText("Live")).toBeInTheDocument();
  });

  it("renders 'Connecting' text when connecting", () => {
    render(<ConnectionDot status="connecting" />);
    expect(screen.getByText("Connecting")).toBeInTheDocument();
  });

  it("renders 'Disconnected' text when disconnected", () => {
    render(<ConnectionDot status="disconnected" />);
    expect(screen.getByText("Disconnected")).toBeInTheDocument();
  });
});
