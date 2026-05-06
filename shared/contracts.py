from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TensorPreview(BaseModel):
    shape: list[int]
    sample_step: int = 1
    data: list[float] = Field(default_factory=list)


class StreamlinePath(BaseModel):
    points: list[list[float]]
    speed: float


class MetricsPayload(BaseModel):
    drag: float
    pressure_peak: float
    velocity_peak: float
    hotspot_ratio: float
    occupancy_ratio: float


class SimulationFrame(BaseModel):
    model_id: str
    step: int
    total_steps: int
    mode: Literal["simulation", "optimization"]
    velocity_field: TensorPreview
    pressure_field: TensorPreview
    drag_map: TensorPreview
    streamlines: list[StreamlinePath]
    metrics: MetricsPayload
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelSummary(BaseModel):
    model_id: str
    filename: str
    format: str
    processed: bool
    optimized_model_id: str | None = None

