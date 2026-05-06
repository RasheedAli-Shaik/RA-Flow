from __future__ import annotations

import threading
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.config import CACHE_DIR, OPTIMIZATION_ITERATIONS, STORAGE_DIR, STREAM_FRAMES
from backend.geometry.importer import supported_suffixes
from backend.geometry.processor import geometry_processor
from backend.optimization.engine import optimization_engine
from backend.physics.engine import physics_engine
from backend.realtime.dispatcher import dispatcher
from backend.storage.repository import ModelRecord, repository
from backend.utils.serialization import load_tensor_bundle, save_tensor_bundle
from shared.contracts import ModelSummary, TensorPreview


router = APIRouter()


class SimulateRequest(BaseModel):
    frames: int = Field(default=STREAM_FRAMES, ge=3, le=60)


class OptimizeRequest(BaseModel):
    iterations: int = Field(default=OPTIMIZATION_ITERATIONS, ge=1, le=20)


def _artifact_url(path: str | Path | None) -> str | None:
    if path is None:
        return None
    path_obj = Path(path).resolve()
    storage_root = STORAGE_DIR.resolve()
    try:
        relative = path_obj.relative_to(storage_root)
    except ValueError:
        return None
    return f"/artifacts/{relative.as_posix()}"


def _record_summary(record: ModelRecord) -> dict:
    return {
        "model": ModelSummary(
            model_id=record.model_id,
            filename=record.filename,
            format=record.format,
            processed=bool(record.processed_tensor_path),
            optimized_model_id=record.optimized_model_id,
        ).model_dump(),
        "assets": {
            "upload_url": _artifact_url(record.upload_path),
            "normalized_url": _artifact_url(record.normalized_mesh_path),
            "optimized_url": _artifact_url(record.optimized_mesh_path),
        },
        "metadata": record.metadata,
        "metrics": record.metrics,
    }


def _process_and_cache(record: ModelRecord) -> tuple[ModelRecord, dict]:
    normalized_path = CACHE_DIR / f"{record.model_id}-normalized.obj"
    processed = geometry_processor.process(Path(record.upload_path), normalized_path)
    tensor_path = CACHE_DIR / f"{record.model_id}.pt"
    bundle = {
        "occupancy": processed.occupancy,
        "sdf": processed.sdf,
        "resolution": processed.resolution,
        "occupancy_ratio": processed.occupancy_ratio,
        "normalized_mesh_path": str(processed.normalized_mesh_path),
    }
    save_tensor_bundle(tensor_path, bundle)
    updated = repository.update(
        record.model_id,
        normalized_mesh_path=str(processed.normalized_mesh_path),
        processed_tensor_path=str(tensor_path),
        metadata={
            **record.metadata,
            "resolution": processed.resolution,
            "occupancy_ratio": processed.occupancy_ratio,
        },
    )
    return updated, bundle


def _load_processed(record: ModelRecord) -> tuple[ModelRecord, dict]:
    if not record.processed_tensor_path or not Path(record.processed_tensor_path).exists():
        return _process_and_cache(record)
    return record, load_tensor_bundle(Path(record.processed_tensor_path))


def _run_simulation_job(model_id: str, bundle: dict, frames: int) -> None:
    dispatcher.emit_status(model_id, "running", {"frames": frames})
    occupancy = bundle["occupancy"]
    sdf = bundle["sdf"]
    for frame in physics_engine.stream_frames(model_id, occupancy, sdf, total_steps=frames):
        dispatcher.emit_frame(frame)
    fields = physics_engine.infer_fields(occupancy, sdf)
    repository.update(model_id, metrics=fields.metrics.model_dump())
    dispatcher.emit_status(model_id, "completed", fields.metrics.model_dump())


@router.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


@router.post("/upload")
async def upload_model(file: UploadFile = File(...)) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in supported_suffixes():
        raise HTTPException(
            status_code=400,
            detail=f"Supported formats are: {', '.join(sorted(supported_suffixes()))}",
        )

    record = repository.create(file.filename or f"model{suffix}", suffix)
    content = await file.read()
    Path(record.upload_path).write_bytes(content)
    return {
        "model_id": record.model_id,
        **_record_summary(record),
    }


@router.get("/models/{model_id}")
def get_model(model_id: str) -> dict:
    try:
        record = repository.get(model_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Model not found") from exc
    return _record_summary(record)


@router.post("/process/{model_id}")
def process_model(model_id: str) -> dict:
    try:
        record = repository.get(model_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Model not found") from exc
    record, bundle = _load_processed(record)
    occupancy = bundle["occupancy"]
    preview = TensorPreview(shape=list(occupancy.shape), sample_step=1, data=occupancy.flatten().tolist())
    sdf_preview = TensorPreview(
        shape=list(bundle["sdf"][..., ::2, ::2, ::2].shape),
        sample_step=2,
        data=bundle["sdf"][..., ::2, ::2, ::2].flatten().tolist(),
    )
    return {
        **_record_summary(record),
        "voxel_grid": preview.model_dump(),
        "sdf_preview": sdf_preview.model_dump(),
    }


@router.post("/simulate/{model_id}")
def simulate_model(model_id: str, payload: SimulateRequest | None = None) -> dict:
    request = payload or SimulateRequest()
    try:
        record = repository.get(model_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Model not found") from exc
    record, bundle = _load_processed(record)
    worker = threading.Thread(
        target=_run_simulation_job,
        args=(record.model_id, bundle, request.frames),
        daemon=True,
    )
    worker.start()
    return {
        "status": "started",
        "model_id": record.model_id,
        "frames": request.frames,
        "socket_event": "simulation_frame",
        "socket_room": f"model:{record.model_id}",
    }


@router.post("/optimize/{model_id}")
def optimize_model(model_id: str, payload: OptimizeRequest | None = None) -> dict:
    request = payload or OptimizeRequest()
    try:
        record = repository.get(model_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Model not found") from exc
    record, bundle = _load_processed(record)
    dispatcher.emit_status(record.model_id, "optimizing", {"iterations": request.iterations})
    mesh_path = Path(record.normalized_mesh_path or record.upload_path)
    mesh = geometry_processor.load_mesh(mesh_path)
    optimized_path = repository.optimized_artifact_path(record.model_id)
    result = optimization_engine.optimize(
        record.model_id,
        mesh,
        bundle["occupancy"],
        bundle["sdf"],
        optimized_path,
        iterations=request.iterations,
    )
    for frame in result.frames:
        dispatcher.emit_frame(frame)

    optimized_record = repository.create_optimized_variant(record, result.best_mesh_path)
    optimized_tensor_path = CACHE_DIR / f"{optimized_record.model_id}.pt"
    optimized_bundle = {
        "occupancy": result.best_occupancy,
        "sdf": result.best_sdf,
        "resolution": bundle["resolution"],
        "occupancy_ratio": result.best_fields.metrics.occupancy_ratio,
        "normalized_mesh_path": str(result.best_mesh_path),
    }
    save_tensor_bundle(optimized_tensor_path, optimized_bundle)
    optimized_record = repository.update(
        optimized_record.model_id,
        processed_tensor_path=str(optimized_tensor_path),
        metrics=result.best_fields.metrics.model_dump(),
        normalized_mesh_path=str(result.best_mesh_path),
        metadata={
            **record.metadata,
            "resolution": bundle["resolution"],
            "source_model_id": record.model_id,
            "occupancy_ratio": result.best_fields.metrics.occupancy_ratio,
        },
    )
    repository.update(record.model_id, metrics=result.best_fields.metrics.model_dump())
    dispatcher.emit_status(
        record.model_id,
        "optimization_completed",
        {
            "optimized_model_id": optimized_record.model_id,
            "baseline_drag": result.baseline_drag,
            "optimized_drag": result.optimized_drag,
        },
    )
    return {
        "model_id": record.model_id,
        "optimized_model_id": optimized_record.model_id,
        "baseline_drag": result.baseline_drag,
        "optimized_drag": result.optimized_drag,
        "improvement_pct": ((result.baseline_drag - result.optimized_drag) / max(result.baseline_drag, 1e-6)) * 100.0,
        "optimized_model": _record_summary(optimized_record),
    }
