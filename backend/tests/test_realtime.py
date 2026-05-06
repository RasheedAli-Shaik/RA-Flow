from __future__ import annotations

from backend.realtime.dispatcher import dispatcher
from backend.realtime.socket_server import socket_app, socketio
from shared.contracts import MetricsPayload, SimulationFrame, TensorPreview


def test_realtime_dispatcher_emits_simulation_frame():
    client = socketio.test_client(socket_app)
    client.emit("join_model", {"model_id": "demo-model"})

    frame = SimulationFrame(
        model_id="demo-model",
        step=1,
        total_steps=1,
        mode="simulation",
        velocity_field=TensorPreview(shape=[1, 3, 2, 2, 2], sample_step=1, data=[0.0] * 24),
        pressure_field=TensorPreview(shape=[1, 1, 2, 2, 2], sample_step=1, data=[0.0] * 8),
        drag_map=TensorPreview(shape=[1, 1, 2, 2, 2], sample_step=1, data=[0.0] * 8),
        streamlines=[],
        metrics=MetricsPayload(
            drag=1.0,
            pressure_peak=0.5,
            velocity_peak=0.75,
            hotspot_ratio=0.1,
            occupancy_ratio=0.2,
        ),
        metadata={},
    )

    dispatcher.emit_frame(frame)
    received = client.get_received()

    assert any(event["name"] == "simulation_frame" for event in received)
    client.disconnect()

