export type TensorPreview = {
  shape: number[];
  sample_step: number;
  data: number[];
};

export type StreamlinePath = {
  points: number[][];
  speed: number;
};

export type MetricsPayload = {
  drag: number;
  pressure_peak: number;
  velocity_peak: number;
  hotspot_ratio: number;
  occupancy_ratio: number;
};

export type SimulationFrame = {
  model_id: string;
  step: number;
  total_steps: number;
  mode: "simulation" | "optimization";
  velocity_field: TensorPreview;
  pressure_field: TensorPreview;
  drag_map: TensorPreview;
  streamlines: StreamlinePath[];
  metrics: MetricsPayload;
  metadata: Record<string, unknown>;
};
