from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router
from backend.config import STORAGE_DIR
from backend.utils.paths import ensure_runtime_dirs


ensure_runtime_dirs()

app = FastAPI(title="RA-Flow v2", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.mount("/artifacts", StaticFiles(directory=STORAGE_DIR), name="artifacts")

