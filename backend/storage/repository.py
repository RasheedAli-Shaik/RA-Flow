from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from backend.config import DATA_DIR, OPTIMIZED_DIR, UPLOAD_DIR
from backend.utils.paths import ensure_runtime_dirs


class ModelRecord(BaseModel):
    model_id: str
    filename: str
    format: str
    upload_path: str
    normalized_mesh_path: str | None = None
    processed_tensor_path: str | None = None
    optimized_mesh_path: str | None = None
    optimized_model_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)


class ModelRepository:
    def __init__(self, manifest_path: Path | None = None) -> None:
        ensure_runtime_dirs()
        self.manifest_path = manifest_path or DATA_DIR / "models.json"
        self._lock = threading.Lock()
        if not self.manifest_path.exists():
            self.manifest_path.write_text("{}")

    def _load(self) -> dict[str, dict[str, Any]]:
        return json.loads(self.manifest_path.read_text())

    def _save(self, payload: dict[str, dict[str, Any]]) -> None:
        self.manifest_path.write_text(json.dumps(payload, indent=2))

    def create(self, filename: str, suffix: str) -> ModelRecord:
        model_id = uuid.uuid4().hex[:12]
        upload_path = UPLOAD_DIR / f"{model_id}{suffix}"
        record = ModelRecord(
            model_id=model_id,
            filename=filename,
            format=suffix.lower().replace(".", ""),
            upload_path=str(upload_path),
        )
        with self._lock:
            data = self._load()
            data[model_id] = record.model_dump()
            self._save(data)
        return record

    def get(self, model_id: str) -> ModelRecord:
        with self._lock:
            data = self._load()
            if model_id not in data:
                raise KeyError(model_id)
            return ModelRecord.model_validate(data[model_id])

    def update(self, model_id: str, **updates: Any) -> ModelRecord:
        with self._lock:
            data = self._load()
            if model_id not in data:
                raise KeyError(model_id)
            current = ModelRecord.model_validate(data[model_id])
            updated = current.model_copy(update=updates)
            data[model_id] = updated.model_dump()
            self._save(data)
        return updated

    def create_optimized_variant(self, source: ModelRecord, optimized_mesh_path: Path) -> ModelRecord:
        candidate = self.create(f"{source.filename.rsplit('.', 1)[0]}-optimized.obj", ".obj")
        optimized_upload = Path(candidate.upload_path)
        optimized_upload.write_bytes(optimized_mesh_path.read_bytes())
        updated_candidate = self.update(
            candidate.model_id,
            normalized_mesh_path=str(optimized_mesh_path),
            optimized_mesh_path=str(optimized_upload),
            metadata={**source.metadata, "source_model_id": source.model_id, "optimized": True},
        )
        self.update(
            source.model_id,
            optimized_model_id=updated_candidate.model_id,
            optimized_mesh_path=str(optimized_upload),
        )
        return updated_candidate

    def optimized_artifact_path(self, model_id: str) -> Path:
        return OPTIMIZED_DIR / f"{model_id}.obj"


repository = ModelRepository()

