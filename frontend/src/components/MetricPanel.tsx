import type { MetricsPayload } from "@shared/contracts";

type Props = {
  metrics?: Partial<MetricsPayload>;
  optimization?: {
    baseline_drag: number;
    optimized_drag: number;
    improvement_pct: number;
  } | null;
};

function metricValue(value?: number, digits = 3) {
  return typeof value === "number" ? value.toFixed(digits) : "--";
}

export function MetricPanel({ metrics, optimization }: Props) {
  return (
    <aside className="panel-sheen flex h-full flex-col gap-4 rounded-[28px] border border-white/10 p-5">
      <div>
        <p className="text-xs uppercase tracking-[0.35em] text-frost/70">Live Metrics</p>
        <h2 className="mt-3 font-display text-2xl font-bold text-paper">Flow Diagnostics</h2>
      </div>

      <div className="grid gap-3">
        <div className="metric-card rounded-3xl p-4">
          <p className="text-xs uppercase tracking-[0.25em] text-paper/45">Drag</p>
          <p className="mt-3 text-3xl font-bold text-ember">{metricValue(metrics?.drag)}</p>
        </div>
        <div className="metric-card rounded-3xl p-4">
          <p className="text-xs uppercase tracking-[0.25em] text-paper/45">Pressure Peak</p>
          <p className="mt-3 text-2xl font-semibold text-paper">{metricValue(metrics?.pressure_peak)}</p>
        </div>
        <div className="metric-card rounded-3xl p-4">
          <p className="text-xs uppercase tracking-[0.25em] text-paper/45">Velocity Peak</p>
          <p className="mt-3 text-2xl font-semibold text-paper">{metricValue(metrics?.velocity_peak)}</p>
        </div>
        <div className="metric-card rounded-3xl p-4">
          <p className="text-xs uppercase tracking-[0.25em] text-paper/45">Hotspot Ratio</p>
          <p className="mt-3 text-2xl font-semibold text-paper">{metricValue(metrics?.hotspot_ratio)}</p>
        </div>
        <div className="metric-card rounded-3xl p-4">
          <p className="text-xs uppercase tracking-[0.25em] text-paper/45">Occupancy Ratio</p>
          <p className="mt-3 text-2xl font-semibold text-paper">{metricValue(metrics?.occupancy_ratio)}</p>
        </div>
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/5 p-4">
        <p className="text-xs uppercase tracking-[0.25em] text-paper/45">Optimization</p>
        <p className="mt-3 text-sm leading-6 text-paper/75">
          Baseline drag: <span className="font-semibold text-paper">{metricValue(optimization?.baseline_drag)}</span>
        </p>
        <p className="text-sm leading-6 text-paper/75">
          Optimized drag: <span className="font-semibold text-paper">{metricValue(optimization?.optimized_drag)}</span>
        </p>
        <p className="mt-2 text-lg font-semibold text-neon">
          {optimization ? `${optimization.improvement_pct.toFixed(2)}% improvement` : "No optimization run yet"}
        </p>
      </div>
    </aside>
  );
}
