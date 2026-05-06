from __future__ import annotations

from shared.contracts import SimulationFrame

from backend.realtime.payloads import frame_to_socket_payload
from backend.realtime.socket_server import socketio


class RealtimeDispatcher:
    def emit_frame(self, frame: SimulationFrame) -> None:
        socketio.emit("simulation_frame", frame_to_socket_payload(frame), room=f"model:{frame.model_id}")

    def emit_status(self, model_id: str, status: str, details: dict | None = None) -> None:
        socketio.emit(
            "simulation_status",
            {"model_id": model_id, "status": status, "details": details or {}},
            room=f"model:{model_id}",
        )


dispatcher = RealtimeDispatcher()
