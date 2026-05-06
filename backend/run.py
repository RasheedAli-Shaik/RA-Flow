from __future__ import annotations

import threading

import uvicorn

from backend.api.app import app
from backend.config import API_HOST, API_PORT
from backend.realtime.socket_server import run_socket_server


def main() -> None:
    socket_thread = threading.Thread(target=run_socket_server, daemon=True)
    socket_thread.start()
    uvicorn.run(app, host=API_HOST, port=API_PORT)


if __name__ == "__main__":
    main()
