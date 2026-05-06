from __future__ import annotations

import trimesh

from backend.geometry.processor import geometry_processor
from backend.optimization.engine import optimization_engine
from backend.physics.engine import physics_engine


def test_geometry_processing_generates_voxels_and_sdf(sample_mesh_file, workspace_tmp_dir):
    normalized_path = workspace_tmp_dir / "normalized.obj"
    processed = geometry_processor.process(sample_mesh_file, normalized_path)

    assert processed.occupancy.shape == (1, 64, 64, 64)
    assert processed.sdf.shape == (1, 64, 64, 64)
    assert 0 < processed.occupancy_ratio < 1
    assert normalized_path.exists()


def test_stream_frames_return_visualizable_payload(sample_mesh: trimesh.Trimesh):
    occupancy, sdf, _ = geometry_processor.tensorize_mesh(sample_mesh)

    frames = list(physics_engine.stream_frames("demo-model", occupancy, sdf, total_steps=3))

    assert len(frames) == 3
    assert frames[0].velocity_field.shape[1] == 3
    assert frames[0].pressure_field.shape[1] == 1
    assert frames[0].metrics.drag >= 0
    assert frames[0].model_id == "demo-model"


def test_optimization_reduces_or_matches_drag(sample_mesh: trimesh.Trimesh, workspace_tmp_dir):
    occupancy, sdf, _ = geometry_processor.tensorize_mesh(sample_mesh)
    result = optimization_engine.optimize(
        "demo-model",
        sample_mesh,
        occupancy,
        sdf,
        workspace_tmp_dir / "optimized.obj",
        iterations=4,
    )

    assert result.best_mesh_path.exists()
    assert result.optimized_drag <= result.baseline_drag + 1e-6
    assert len(result.frames) == 5
