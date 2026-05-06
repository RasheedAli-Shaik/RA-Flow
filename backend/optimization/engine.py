from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import trimesh

from backend.config import DEFAULT_WIND_VECTOR, OPTIMIZATION_ITERATIONS, OPTIMIZATION_STEP
from backend.geometry.processor import geometry_processor
from backend.physics.engine import FieldBundle, physics_engine
from shared.contracts import SimulationFrame


@dataclass(slots=True)
class OptimizationResult:
    best_mesh_path: Path
    best_fields: FieldBundle
    best_occupancy: torch.Tensor
    best_sdf: torch.Tensor
    baseline_drag: float
    optimized_drag: float
    frames: list[SimulationFrame]


class OptimizationEngine:
    def _sample_grid(self, field: np.ndarray, points: np.ndarray) -> np.ndarray:
        grid_size = field.shape[0]
        coords = np.rint(((points + 1.0) * 0.5) * (grid_size - 1)).astype(np.int32)
        coords = np.clip(coords, 0, grid_size - 1)
        return field[coords[:, 0], coords[:, 1], coords[:, 2]]

    def _deform_mesh(self, mesh: trimesh.Trimesh, hotspot_map: np.ndarray, intensity: float) -> trimesh.Trimesh:
        candidate = mesh.copy()
        normals = candidate.vertex_normals
        hotspot_values = self._sample_grid(hotspot_map, candidate.vertices)
        hotspot_values = hotspot_values / max(1e-6, float(np.max(hotspot_values)))
        wind = np.asarray(DEFAULT_WIND_VECTOR, dtype=np.float32)
        wind = wind / max(np.linalg.norm(wind), 1e-6)
        alignment = np.abs(normals @ wind)
        displacement = -normals * hotspot_values[:, None] * (0.5 + 0.5 * alignment[:, None]) * intensity
        candidate.vertices = candidate.vertices + displacement
        taper = 1.0 - 0.015 * (0.5 + hotspot_values.mean())
        candidate.vertices[:, 1] *= taper
        candidate.vertices[:, 2] *= taper
        candidate.vertices[:, 0] *= 1.0 + 0.006 * intensity / max(OPTIMIZATION_STEP, 1e-6)
        trimesh.smoothing.filter_laplacian(candidate, lamb=0.32, iterations=3)
        return candidate

    def _fallback_candidate(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        candidate = mesh.copy()
        candidate.vertices[:, 1] *= 0.92
        candidate.vertices[:, 2] *= 0.92
        candidate.vertices[:, 0] *= 1.04
        trimesh.smoothing.filter_laplacian(candidate, lamb=0.4, iterations=4)
        return candidate

    def optimize(
        self,
        model_id: str,
        mesh: trimesh.Trimesh,
        occupancy,
        sdf,
        output_path: Path,
        iterations: int = OPTIMIZATION_ITERATIONS,
    ) -> OptimizationResult:
        baseline_fields = physics_engine.infer_fields(occupancy, sdf)
        best_mesh = mesh.copy()
        best_occupancy = occupancy.clone()
        best_sdf = sdf.clone()
        best_fields = baseline_fields
        best_drag = baseline_fields.metrics.drag
        frames = [physics_engine.build_frame(model_id, baseline_fields, occupancy, 1, iterations + 1, "optimization")]

        for iteration in range(iterations):
            hotspot_np = best_fields.hotspot_map.squeeze(0).squeeze(0).numpy()
            candidate_mesh = self._deform_mesh(
                best_mesh,
                hotspot_np,
                OPTIMIZATION_STEP * (1.0 - 0.35 * (iteration / max(iterations, 1))),
            )
            candidate_occupancy, candidate_sdf, _ = geometry_processor.tensorize_mesh(candidate_mesh)
            candidate_fields = physics_engine.infer_fields(candidate_occupancy, candidate_sdf)
            if candidate_fields.metrics.drag < best_drag:
                best_drag = candidate_fields.metrics.drag
                best_mesh = candidate_mesh
                best_occupancy = candidate_occupancy
                best_sdf = candidate_sdf
                best_fields = candidate_fields
            frames.append(
                physics_engine.build_frame(
                    model_id,
                    best_fields,
                    best_occupancy,
                    iteration + 2,
                    iterations + 1,
                    "optimization",
                )
            )

        if best_fields.metrics.drag >= baseline_fields.metrics.drag:
            fallback_mesh = self._fallback_candidate(best_mesh)
            fallback_occupancy, fallback_sdf, _ = geometry_processor.tensorize_mesh(fallback_mesh)
            fallback_fields = physics_engine.infer_fields(fallback_occupancy, fallback_sdf)
            if fallback_fields.metrics.drag <= best_fields.metrics.drag:
                best_mesh = fallback_mesh
                best_occupancy = fallback_occupancy
                best_sdf = fallback_sdf
                best_fields = fallback_fields
                best_drag = fallback_fields.metrics.drag
                frames[-1] = physics_engine.build_frame(
                    model_id,
                    best_fields,
                    best_occupancy,
                    iterations + 1,
                    iterations + 1,
                    "optimization",
                )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        best_mesh.export(output_path)
        return OptimizationResult(
            best_mesh_path=output_path,
            best_fields=best_fields,
            best_occupancy=best_occupancy,
            best_sdf=best_sdf,
            baseline_drag=baseline_fields.metrics.drag,
            optimized_drag=best_drag,
            frames=frames,
        )


optimization_engine = OptimizationEngine()
