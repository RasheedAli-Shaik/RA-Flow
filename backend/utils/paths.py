from __future__ import annotations

from backend.config import CACHE_DIR, DATA_DIR, LOG_DIR, OPTIMIZED_DIR, UPLOAD_DIR


def ensure_runtime_dirs() -> None:
    for path in (DATA_DIR, UPLOAD_DIR, OPTIMIZED_DIR, CACHE_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)

