from __future__ import annotations

import json
import uuid
from pathlib import Path

from backend.config import CACHE_DIR, OPTIMIZED_DIR
from backend.geometry.processor import geometry_processor
from backend.optimization.engine import optimization_engine
from backend.physics.engine import physics_engine
from backend.utils.paths import ensure_runtime_dirs


def run_direct_pipeline(input_path: Path) -> dict:
    ensure_runtime_dirs()
    run_id = uuid.uuid4().hex[:10]
    normalized_path = CACHE_DIR / f"{run_id}-normalized.obj"
    processed = geometry_processor.process(input_path, normalized_path)
    fields = physics_engine.infer_fields(processed.occupancy, processed.sdf)
    optimized_path = OPTIMIZED_DIR / f"{run_id}-optimized.obj"
    optimization = optimization_engine.optimize(
        run_id,
        processed.mesh,
        processed.occupancy,
        processed.sdf,
        optimized_path,
        iterations=6,
    )
    return {
        "run_id": run_id,
        "input_path": str(input_path),
        "normalized_mesh_path": str(normalized_path),
        "optimized_mesh_path": str(optimized_path),
        "resolution": processed.resolution,
        "occupancy_ratio": processed.occupancy_ratio,
        "baseline_metrics": fields.metrics.model_dump(),
        "optimized_drag": optimization.optimized_drag,
        "baseline_drag": optimization.baseline_drag,
        "improvement_pct": ((optimization.baseline_drag - optimization.optimized_drag) / max(optimization.baseline_drag, 1e-6))
        * 100.0,
        "optimization_frames": len(optimization.frames),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the RA-Flow pipeline directly against a file path.")
    parser.add_argument("input_path", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    result = run_direct_pipeline(args.input_path)
    payload = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
