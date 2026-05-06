from __future__ import annotations

from dataclasses import dataclass

import trimesh

from backend.geometry.processor import GeometryProcessor


@dataclass(slots=True)
class MultiResolutionBundle:
    resolution: int
    occupancy: object
    sdf: object
    occupancy_ratio: float


def build_multiresolution_pyramid(
    mesh: trimesh.Trimesh,
    resolutions: tuple[int, ...] = (32, 64, 128),
) -> dict[int, MultiResolutionBundle]:
    pyramid: dict[int, MultiResolutionBundle] = {}
    for resolution in resolutions:
        processor = GeometryProcessor(resolution=resolution)
        occupancy, sdf, occupancy_ratio = processor.tensorize_mesh(mesh)
        pyramid[resolution] = MultiResolutionBundle(
            resolution=resolution,
            occupancy=occupancy,
            sdf=sdf,
            occupancy_ratio=occupancy_ratio,
        )
    return pyramid

