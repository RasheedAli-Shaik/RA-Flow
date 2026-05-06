import type { ModelEnvelope } from "@/types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `Request failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

export function apiAssetUrl(path?: string | null): string | undefined {
  if (!path) {
    return undefined;
  }
  return path.startsWith("http") ? path : `${API_URL}${path}`;
}

export async function uploadModel(file: File): Promise<ModelEnvelope & { model_id: string }> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_URL}/upload`, {
    method: "POST",
    body: formData,
  });
  return parseJson<ModelEnvelope & { model_id: string }>(response);
}

export async function processModel(modelId: string): Promise<ModelEnvelope> {
  const response = await fetch(`${API_URL}/process/${modelId}`, {
    method: "POST",
  });
  return parseJson<ModelEnvelope>(response);
}

export async function simulateModel(modelId: string, frames = 18): Promise<{ status: string }> {
  const response = await fetch(`${API_URL}/simulate/${modelId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ frames }),
  });
  return parseJson<{ status: string }>(response);
}

export async function optimizeModel(
  modelId: string,
  iterations = 8,
): Promise<
  ModelEnvelope & {
    model_id: string;
    optimized_model_id: string;
    baseline_drag: number;
    optimized_drag: number;
    improvement_pct: number;
    optimized_model: ModelEnvelope;
  }
> {
  const response = await fetch(`${API_URL}/optimize/${modelId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ iterations }),
  });
  return parseJson(response);
}

