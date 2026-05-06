from __future__ import annotations

import argparse
import functools
import json
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import requests
import socketio as socketio_client
import uvicorn

from backend.api.app import app
from backend.realtime.socket_server import run_socket_server


ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = ROOT / "frontend" / "dist"


def _wait_for(url: str, timeout: float = 60.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(url, timeout=3)
            if response.ok:
                return
        except Exception:
            time.sleep(0.5)
            continue
        time.sleep(0.5)
    raise TimeoutError(f"Timed out waiting for {url}")


def start_api_server() -> uvicorn.Server:
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    _wait_for("http://127.0.0.1:8000/health")
    return server


def start_socket_thread() -> threading.Thread:
    thread = threading.Thread(target=run_socket_server, daemon=True)
    thread.start()
    time.sleep(2.0)
    return thread


def start_frontend_server() -> ThreadingHTTPServer:
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(FRONTEND_DIST))
    server = ThreadingHTTPServer(("127.0.0.1", 5173), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    _wait_for("http://127.0.0.1:5173")
    return server


def exercise_model(file_path: Path, simulate_frames: int = 4) -> dict[str, Any]:
    frames: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    client = socketio_client.Client(reconnection=False, request_timeout=30)

    @client.on("simulation_frame")
    def on_frame(payload):
        frames.append(payload)

    @client.on("simulation_status")
    def on_status(payload):
        statuses.append(payload)

    with file_path.open("rb") as stream:
        upload_response = requests.post(
            "http://127.0.0.1:8000/upload",
            files={"file": (file_path.name, stream, "application/octet-stream")},
            timeout=300,
        )
    upload_response.raise_for_status()
    uploaded = upload_response.json()
    model_id = uploaded["model_id"]

    process_response = requests.post(f"http://127.0.0.1:8000/process/{model_id}", timeout=600)
    process_response.raise_for_status()
    processed = process_response.json()

    client.connect("http://127.0.0.1:8001", transports=["polling"])
    client.emit("join_model", {"model_id": model_id})

    simulate_response = requests.post(
        f"http://127.0.0.1:8000/simulate/{model_id}",
        json={"frames": simulate_frames},
        timeout=120,
    )
    simulate_response.raise_for_status()

    start = time.time()
    while time.time() - start < 180:
        if any(status.get("status") == "completed" for status in statuses):
            break
        time.sleep(0.5)

    optimize_response = requests.post(
        f"http://127.0.0.1:8000/optimize/{model_id}",
        json={"iterations": 6},
        timeout=900,
    )
    optimize_response.raise_for_status()
    optimized = optimize_response.json()

    start = time.time()
    while time.time() - start < 180:
        if any(status.get("status") == "optimization_completed" for status in statuses):
            break
        time.sleep(0.5)

    client.disconnect()

    if not frames:
        raise AssertionError(f"No realtime frames were received for {file_path.name}")
    if optimized["optimized_drag"] > optimized["baseline_drag"]:
        raise AssertionError(f"Optimization regressed drag for {file_path.name}")

    return {
        "file": str(file_path),
        "model_id": model_id,
        "normalized_url": processed["assets"]["normalized_url"],
        "simulation_frames_received": len(frames),
        "statuses": statuses,
        "baseline_drag": optimized["baseline_drag"],
        "optimized_drag": optimized["optimized_drag"],
        "improvement_pct": optimized["improvement_pct"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a full-stack RA-Flow smoke test.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "backend" / "storage" / "logs" / "e2e-summary.json")
    args = parser.parse_args()

    if not FRONTEND_DIST.exists():
        raise FileNotFoundError("frontend/dist does not exist. Run `npm --prefix frontend run build` first.")

    api_server = start_api_server()
    socket_thread = start_socket_thread()
    frontend_server = start_frontend_server()
    results = []
    try:
        for file_path in args.files:
            results.append(exercise_model(file_path.resolve()))
    finally:
        api_server.should_exit = True
        frontend_server.shutdown()
        frontend_server.server_close()
        time.sleep(1.0)

    summary = {
        "frontend_url": "http://127.0.0.1:5173",
        "api_url": "http://127.0.0.1:8000",
        "socket_transport": "polling",
        "files": results,
        "socket_thread_alive": socket_thread.is_alive(),
    }
    args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
