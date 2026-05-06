from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

import pytest
import trimesh

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.geometry.processor import geometry_processor


@pytest.fixture()
def sample_mesh() -> trimesh.Trimesh:
    mesh = trimesh.creation.box(extents=(1.0, 0.55, 0.38))
    return geometry_processor.normalize_mesh(mesh)


@pytest.fixture()
def workspace_tmp_dir() -> Path:
    temp_dir = ROOT / "backend" / "storage" / "test_tmp" / uuid.uuid4().hex
    temp_dir.mkdir(parents=True, exist_ok=True)
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture()
def sample_mesh_file(workspace_tmp_dir: Path) -> Path:
    mesh = trimesh.creation.box(extents=(1.0, 0.55, 0.38))
    path = workspace_tmp_dir / "sample.obj"
    mesh.export(path)
    return path
