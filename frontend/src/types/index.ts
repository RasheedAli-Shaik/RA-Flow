import type { MetricsPayload, SimulationFrame, TensorPreview } from "@shared/contracts";

export type ViewerMode = "geometry" | "pressure" | "streamlines" | "optimization";

export type ModelEnvelope = {
  model: {
    model_id: string;
    filename: string;
    format: string;
    processed: boolean;
    optimized_model_id?: string | null;
  };
  assets: {
    upload_url?: string | null;
    normalized_url?: string | null;
    optimized_url?: string | null;
  };
  metadata: Record<string, unknown>;
  metrics: Partial<MetricsPayload>;
  voxel_grid?: TensorPreview;
  sdf_preview?: TensorPreview;
};

export type SocketStatus = {
  status: string;
  model_id?: string;
  details?: Record<string, unknown>;
};

export type LiveState = {
  frame: SimulationFrame | null;
  status: SocketStatus;
};

