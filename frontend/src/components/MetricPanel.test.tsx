import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MetricPanel } from "./MetricPanel";

describe("MetricPanel", () => {
  it("renders live metrics and optimization deltas", () => {
    render(
      <MetricPanel
        metrics={{
          drag: 1.234,
          pressure_peak: 2.345,
          velocity_peak: 3.456,
          hotspot_ratio: 0.123,
          occupancy_ratio: 0.234,
        }}
        optimization={{
          baseline_drag: 1.5,
          optimized_drag: 1.2,
          improvement_pct: 20,
        }}
      />,
    );

    expect(screen.getByText("1.234")).toBeInTheDocument();
    expect(screen.getByText("20.00% improvement")).toBeInTheDocument();
  });
});
