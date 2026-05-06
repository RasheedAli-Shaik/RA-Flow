from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
import trimesh


@dataclass(slots=True)
class ProcessedGeometry:
    mesh: trimesh.Trimesh
    occupancy: torch.Tensor
    sdf: torch.Tensor
    resolution: int
    occupancy_ratio: float
    normalized_mesh_path: Path

