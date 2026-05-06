import { io } from "socket.io-client";

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL ?? "http://localhost:8001";

export function createSimulationSocket() {
  return io(SOCKET_URL, {
    // Polling is the most stable local transport on the Windows/Werkzeug dev stack.
    transports: ["polling"],
    upgrade: false,
    withCredentials: false,
  });
}

