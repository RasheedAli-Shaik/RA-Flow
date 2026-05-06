from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import trimesh
from scipy.ndimage import distance_transform_edt, gaussian_filter

from backend.geometry.importer import load_supported_mesh
from backend.geometry.types import ProcessedGeometry


class GeometryProcessor:
    def __init__(self, resolution: int = 64) -> None:
        self.resolution = resolution
        self.bounds_min = -1.0
        self.bounds_max = 1.0
        self.pitch = (self.bounds_max - self.bounds_min) / resolution

    def load_mesh(self, mesh_path: Path) -> trimesh.Trimesh:
        mesh = load_supported_mesh(mesh_path)
        if mesh.faces is None or len(mesh.faces) == 0:
            raise ValueError(f"Mesh {mesh_path} has no faces")
        if hasattr(mesh, "remove_duplicate_faces"):
            mesh.remove_duplicate_faces()
        if hasattr(mesh, "remove_degenerate_faces"):
            mesh.remove_degenerate_faces()
        if hasattr(mesh, "remove_unreferenced_vertices"):
            mesh.remove_unreferenced_vertices()
        mesh.process(validate=True)
        return mesh

    def normalize_mesh(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        normalized = mesh.copy()
        centroid = normalized.bounding_box.centroid
        normalized.apply_translation(-centroid)
        extents = normalized.extents
        max_extent = float(np.max(extents)) if np.max(extents) > 0 else 1.0
        scale = 1.6 / max_extent
        normalized.apply_scale(scale)
        return normalized

    def mesh_to_voxel(self, mesh: trimesh.Trimesh) -> np.ndarray:
        occupancy = np.zeros((self.resolution, self.resolution, self.resolution), dtype=np.float32)
        voxelized = mesh.voxelized(pitch=self.pitch).fill()
        points = voxelized.points
        indices = np.rint(
            ((points - self.bounds_min) / (self.bounds_max - self.bounds_min)) * (self.resolution - 1)
        ).astype(np.int32)
        indices = np.clip(indices, 0, self.resolution - 1)
        occupancy[indices[:, 0], indices[:, 1], indices[:, 2]] = 1.0
        occupancy = gaussian_filter(occupancy, sigma=0.4)
        occupancy = (occupancy > 0.18).astype(np.float32)
        return occupancy

    def voxel_to_sdf(self, occupancy: np.ndarray) -> np.ndarray:
        inside_distance = distance_transform_edt(occupancy)
        outside_distance = distance_transform_edt(1.0 - occupancy)
        signed = outside_distance - inside_distance
        signed *= self.pitch
        signed = np.clip(signed, -1.5, 1.5)
        return signed.astype(np.float32)

    def tensorize_mesh(self, mesh: trimesh.Trimesh) -> tuple[torch.Tensor, torch.Tensor, float]:
        occupancy = self.mesh_to_voxel(mesh)
        sdf = self.voxel_to_sdf(occupancy)
        occupancy_tensor = torch.from_numpy(occupancy).unsqueeze(0)
        sdf_tensor = torch.from_numpy(sdf).unsqueeze(0)
        return occupancy_tensor.float(), sdf_tensor.float(), float(occupancy.mean())

    def process(self, mesh_path: Path, normalized_mesh_path: Path) -> ProcessedGeometry:
        mesh = self.normalize_mesh(self.load_mesh(mesh_path))
        normalized_mesh_path.parent.mkdir(parents=True, exist_ok=True)
        mesh.export(normalized_mesh_path)
        occupancy_tensor, sdf_tensor, occupancy_ratio = self.tensorize_mesh(mesh)
        return ProcessedGeometry(
            mesh=mesh,
            occupancy=occupancy_tensor.float(),
            sdf=sdf_tensor.float(),
            resolution=self.resolution,
            occupancy_ratio=occupancy_ratio,
            normalized_mesh_path=normalized_mesh_path,
        )


geometry_processor = GeometryProcessor()
