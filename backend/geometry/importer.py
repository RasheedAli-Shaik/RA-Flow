from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import trimesh

SUPPORTED_MESH_SUFFIXES = {".stl", ".obj", ".glb", ".gltf", ".step", ".stp"}


def supported_suffixes() -> set[str]:
    return set(SUPPORTED_MESH_SUFFIXES)


def _scene_to_mesh(scene: trimesh.Scene) -> trimesh.Trimesh:
    meshes = []
    for geometry in scene.geometry.values():
        if isinstance(geometry, trimesh.Trimesh) and len(geometry.vertices) and len(geometry.faces):
            meshes.append(geometry)
    if not meshes:
        raise ValueError("Scene does not contain any triangulated meshes")
    return trimesh.util.concatenate(meshes)


def _load_trimesh_mesh(mesh_path: Path) -> trimesh.Trimesh:
    raw = trimesh.load(mesh_path)
    if isinstance(raw, trimesh.Scene):
        return _scene_to_mesh(raw)
    if not isinstance(raw, trimesh.Trimesh):
        raise ValueError(f"Unsupported mesh type for {mesh_path}")
    return raw


def _step_shape_to_trimesh(mesh_path: Path, linear_tolerance: float = 0.8, angular_tolerance: float = 0.45) -> trimesh.Trimesh:
    try:
        os.environ.setdefault("XDG_CACHE_HOME", str((Path(__file__).resolve().parents[1] / "storage" / "cache").resolve()))
        import cadquery as cq
    except ImportError as exc:
        raise RuntimeError(
            "STEP ingestion requires cadquery. Install it with `python -m pip install cadquery`."
        ) from exc

    workplane = cq.importers.importStep(str(mesh_path))
    values = workplane.vals()
    if not values:
        raise ValueError(f"STEP file {mesh_path} does not contain any solids")

    vertices_accumulator: list[np.ndarray] = []
    faces_accumulator: list[np.ndarray] = []
    vertex_offset = 0
    for value in values:
        vertices, faces = value.tessellate(linear_tolerance, angular_tolerance)
        vertex_array = np.asarray([[vertex.x, vertex.y, vertex.z] for vertex in vertices], dtype=np.float64)
        face_array = np.asarray(faces, dtype=np.int64)
        if not len(vertex_array) or not len(face_array):
            continue
        vertices_accumulator.append(vertex_array)
        faces_accumulator.append(face_array + vertex_offset)
        vertex_offset += len(vertex_array)

    if not vertices_accumulator or not faces_accumulator:
        raise ValueError(f"STEP file {mesh_path} could not be tessellated into a triangle mesh")

    mesh = trimesh.Trimesh(
        vertices=np.concatenate(vertices_accumulator, axis=0),
        faces=np.concatenate(faces_accumulator, axis=0),
        process=False,
    )
    return mesh


def load_supported_mesh(mesh_path: Path) -> trimesh.Trimesh:
    suffix = mesh_path.suffix.lower()
    if suffix not in SUPPORTED_MESH_SUFFIXES:
        raise ValueError(f"Unsupported mesh format: {suffix}")
    if suffix in {".step", ".stp"}:
        return _step_shape_to_trimesh(mesh_path)
    return _load_trimesh_mesh(mesh_path)
