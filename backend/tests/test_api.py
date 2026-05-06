from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.app import app
from backend.api import routes
from backend.storage.repository import ModelRecord


client = TestClient(app)


def test_healthcheck():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_rejects_unsupported_extension():
    response = client.post(
        "/upload",
        files={"file": ("not-a-mesh.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400


def test_upload_persists_supported_mesh(workspace_tmp_dir, monkeypatch):
    upload_path = workspace_tmp_dir / "mesh.obj"

    def fake_create(filename: str, suffix: str) -> ModelRecord:
        return ModelRecord(
            model_id="model123",
            filename=filename,
            format=suffix.replace(".", ""),
            upload_path=str(upload_path),
        )

    monkeypatch.setattr(routes.repository, "create", fake_create)

    response = client.post(
        "/upload",
        files={"file": ("mesh.obj", b"o test\nv 0 0 0\n", "application/octet-stream")},
    )

    assert response.status_code == 200
    assert response.json()["model_id"] == "model123"
    assert Path(upload_path).read_bytes() == b"o test\nv 0 0 0\n"
