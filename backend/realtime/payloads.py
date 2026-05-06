from __future__ import annotations

from shared.contracts import SimulationFrame


def frame_to_socket_payload(frame: SimulationFrame) -> dict:
    return frame.model_dump()

