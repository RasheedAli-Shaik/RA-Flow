from __future__ import annotations

from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room

from backend.config import SOCKET_HOST, SOCKET_PORT


socket_app = Flask("raflow-realtime")
socket_app.config["SECRET_KEY"] = "raflow-v2-secret"
socketio = SocketIO(socket_app, cors_allowed_origins="*", async_mode="threading")


@socketio.on("connect")
def handle_connect():
    emit("server_status", {"status": "connected"})


@socketio.on("disconnect")
def handle_disconnect():
    return None


@socketio.on("join_model")
def handle_join_model(payload: dict):
    model_id = payload.get("model_id")
    if not model_id:
        return
    join_room(f"model:{model_id}")
    emit("server_status", {"status": "joined", "model_id": model_id})


@socketio.on("leave_model")
def handle_leave_model(payload: dict):
    model_id = payload.get("model_id")
    if not model_id:
        return
    leave_room(f"model:{model_id}")
    emit("server_status", {"status": "left", "model_id": model_id})


def run_socket_server() -> None:
    socketio.run(socket_app, host=SOCKET_HOST, port=SOCKET_PORT, allow_unsafe_werkzeug=True)

