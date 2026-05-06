from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterator

import numpy as np
import torch

from backend.config import DEFAULT_WIND_VECTOR, STREAM_FRAMES, STREAM_SAMPLE_STEP
from backend.physics.drag import compute_drag_map
from backend.physics.hotspots import compute_hotspots
from backend.physics.model import PhysicsNeMoSurrogate
from backend.utils.device import clear_device_cache, get_device
from shared.contracts import MetricsPayload, SimulationFrame, StreamlinePath, TensorPreview


@dataclass(slots=True)
class FieldBundle:
    velocity: torch.Tensor
    pressure: torch.Tensor
    drag_map: torch.Tensor
    hotspot_map: torch.Tensor
    metrics: MetricsPayload


class SurrogatePhysicsEngine:
    def __init__(self) -> None:
        self.device = get_device()
        self.model = PhysicsNeMoSurrogate().to(self.device).eval()

    def _wind_tensor(self, batch: int, grid_size: int, wind_vector: tuple[float, float, float]) -> torch.Tensor:
        base = torch.tensor(wind_vector, device=self.device, dtype=torch.float32)
        return base.view(1, 3, 1, 1, 1).repeat(batch, 1, grid_size, grid_size, grid_size)

    def _physics_prior(
        self,
        occupancy: torch.Tensor,
        sdf: torch.Tensor,
        wind_vector: tuple[float, float, float],
    ) -> tuple[torch.Tensor, torch.Tensor]:
        batch, _, size_x, _, _ = occupancy.shape
        wind = self._wind_tensor(batch, size_x, wind_vector)
        wind_unit = torch.nn.functional.normalize(wind[:, :, :1, :1, :1], dim=1, eps=1e-6)
        sdf_grad = torch.gradient(sdf, dim=(2, 3, 4), spacing=(1.0, 1.0, 1.0))
        grad = torch.cat(sdf_grad, dim=1)
        normals = torch.nn.functional.normalize(grad, dim=1, eps=1e-6)
        open_space = torch.sigmoid(sdf * 9.0) * (1.0 - occupancy)
        wind_dot = torch.sum(normals * wind_unit, dim=1, keepdim=True)
        tangential = wind - wind_dot * normals
        prior_velocity = open_space * (0.55 * wind + 0.45 * tangential)
        surface_response = torch.exp(-torch.abs(sdf) * 12.0)
        prior_velocity = prior_velocity + 0.18 * surface_response * normals
        prior_velocity = prior_velocity * (1.0 - occupancy)
        speed = torch.linalg.norm(prior_velocity, dim=1, keepdim=True)
        frontality = torch.relu(-wind_dot) * surface_response
        prior_pressure = 0.4 * surface_response + 0.8 * frontality + 0.2 * (1.0 - speed)
        return prior_velocity, prior_pressure

    def infer_fields(
        self,
        occupancy: torch.Tensor,
        sdf: torch.Tensor,
        wind_vector: tuple[float, float, float] = DEFAULT_WIND_VECTOR,
    ) -> FieldBundle:
        occupancy = occupancy.to(self.device)
        sdf = sdf.to(self.device)
        if occupancy.ndim == 4:
            occupancy = occupancy.unsqueeze(0)
        if sdf.ndim == 4:
            sdf = sdf.unsqueeze(0)

        with torch.no_grad():
            prior_velocity, prior_pressure = self._physics_prior(occupancy, sdf, wind_vector)
            features = torch.cat([occupancy, sdf, prior_velocity, prior_pressure], dim=1)
            residual = self.model(features)
            velocity = (prior_velocity + 0.35 * torch.tanh(residual[:, :3])) * (1.0 - occupancy)
            pressure = torch.relu(prior_pressure + 0.25 * residual[:, 3:4]) * (1.0 - occupancy)
            wind = torch.tensor(wind_vector, device=self.device, dtype=torch.float32)
            drag_map, drag_score = compute_drag_map(pressure, sdf, occupancy, wind)
            hotspot_map = compute_hotspots(velocity, pressure, sdf, occupancy)
            speed = torch.linalg.norm(velocity, dim=1, keepdim=True)
            metrics = MetricsPayload(
                drag=float(drag_score.item()),
                pressure_peak=float(torch.max(pressure).item()),
                velocity_peak=float(torch.max(speed).item()),
                hotspot_ratio=float((hotspot_map > 0.6).float().mean().item()),
                occupancy_ratio=float(occupancy.mean().item()),
            )
        return FieldBundle(
            velocity=velocity.detach().cpu(),
            pressure=pressure.detach().cpu(),
            drag_map=drag_map.detach().cpu(),
            hotspot_map=hotspot_map.detach().cpu(),
            metrics=metrics,
        )

    def _tensor_preview(self, tensor: torch.Tensor, sample_step: int = STREAM_SAMPLE_STEP) -> TensorPreview:
        sampled = tensor[..., ::sample_step, ::sample_step, ::sample_step]
        return TensorPreview(shape=list(sampled.shape), sample_step=sample_step, data=sampled.flatten().tolist())

    def build_frame(
        self,
        model_id: str,
        fields: FieldBundle,
        occupancy: torch.Tensor,
        step: int,
        total_steps: int,
        mode: str,
    ) -> SimulationFrame:
        if occupancy.ndim == 4:
            occupancy = occupancy.unsqueeze(0)
        streamlines = self.trace_streamlines(fields.velocity, occupancy, step / max(1, total_steps))
        return SimulationFrame(
            model_id=model_id,
            step=step,
            total_steps=total_steps,
            mode=mode,  # type: ignore[arg-type]
            velocity_field=self._tensor_preview(fields.velocity),
            pressure_field=self._tensor_preview(fields.pressure),
            drag_map=self._tensor_preview(fields.drag_map),
            streamlines=streamlines,
            metrics=fields.metrics,
            metadata={"device": str(self.device), "resolution": int(fields.velocity.shape[-1])},
        )

    def _field_sample(self, field: np.ndarray, position: np.ndarray) -> np.ndarray:
        grid_size = field.shape[1]
        coords = ((position + 1.0) * 0.5 * (grid_size - 1)).round().astype(int)
        coords = np.clip(coords, 0, grid_size - 1)
        return field[:, coords[0], coords[1], coords[2]]

    def trace_streamlines(
        self,
        velocity: torch.Tensor,
        occupancy: torch.Tensor,
        phase: float = 0.0,
        seeds_per_axis: int = 6,
        steps: int = 28,
    ) -> list[StreamlinePath]:
        velocity_np = velocity.squeeze(0).numpy()
        occupancy_np = occupancy.squeeze(0).squeeze(0).numpy()
        traces: list[StreamlinePath] = []
        yz = np.linspace(-0.75, 0.75, seeds_per_axis)
        seed_offset = 0.1 * math.sin(phase * math.tau)
        for y in yz:
            for z in yz[::2]:
                position = np.array([-0.92, y + seed_offset, z], dtype=np.float32)
                points = [position.tolist()]
                speed_accumulator = []
                for _ in range(steps):
                    coords = ((position + 1.0) * 0.5 * (occupancy_np.shape[0] - 1)).round().astype(int)
                    coords = np.clip(coords, 0, occupancy_np.shape[0] - 1)
                    if occupancy_np[coords[0], coords[1], coords[2]] > 0.2:
                        break
                    velocity_sample = self._field_sample(velocity_np, position)
                    speed = float(np.linalg.norm(velocity_sample))
                    if speed < 1e-4:
                        break
                    direction = velocity_sample / (speed + 1e-6)
                    position = position + direction * (0.08 + 0.02 * speed)
                    if np.any(position < -1.0) or np.any(position > 1.0):
                        break
                    points.append(position.tolist())
                    speed_accumulator.append(speed)
                if len(points) > 4:
                    traces.append(
                        StreamlinePath(
                            points=points,
                            speed=float(np.mean(speed_accumulator) if speed_accumulator else 0.0),
                        )
                    )
        return traces

    def stream_frames(
        self,
        model_id: str,
        occupancy: torch.Tensor,
        sdf: torch.Tensor,
        mode: str = "simulation",
        total_steps: int = STREAM_FRAMES,
    ) -> Iterator[SimulationFrame]:
        fields = self.infer_fields(occupancy, sdf)
        for step in range(total_steps):
            phase = step / max(1, total_steps)
            animated_fields = FieldBundle(
                velocity=fields.velocity * (1.0 + 0.015 * math.sin(phase * math.tau)),
                pressure=fields.pressure * (1.0 + 0.01 * math.cos(phase * math.tau)),
                drag_map=fields.drag_map,
                hotspot_map=fields.hotspot_map,
                metrics=fields.metrics,
            )
            yield self.build_frame(model_id, animated_fields, occupancy, step + 1, total_steps, mode)
        clear_device_cache()


physics_engine = SurrogatePhysicsEngine()
