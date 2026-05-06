from __future__ import annotations

from pathlib import Path
from typing import Any

import torch


def save_tensor_bundle(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, path)


def load_tensor_bundle(path: Path) -> dict[str, Any]:
    return torch.load(path, map_location="cpu")
