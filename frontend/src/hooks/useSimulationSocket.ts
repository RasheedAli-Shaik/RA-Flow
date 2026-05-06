import { startTransition, useEffect, useState } from "react";
import type { SimulationFrame } from "@shared/contracts";
import type { LiveState, SocketStatus } from "@/types";
import { createSimulationSocket } from "@/lib/socket";

export function useSimulationSocket(modelId?: string): LiveState {
  const [frame, setFrame] = useState<SimulationFrame | null>(null);
  const [status, setStatus] = useState<SocketStatus>({ status: "idle" });

  useEffect(() => {
    if (!modelId) {
      setStatus({ status: "awaiting-model" });
      return;
    }

    const socket = createSimulationSocket();

    socket.on("connect", () => {
      startTransition(() => {
        setStatus({ status: "connected", model_id: modelId });
      });
      socket.emit("join_model", { model_id: modelId });
    });

    socket.on("simulation_frame", (payload: SimulationFrame) => {
      startTransition(() => {
        setFrame(payload);
      });
    });

    socket.on("simulation_status", (payload: SocketStatus) => {
      startTransition(() => {
        setStatus(payload);
      });
    });

    socket.on("server_status", (payload: SocketStatus) => {
      startTransition(() => {
        setStatus(payload);
      });
    });

    return () => {
      socket.emit("leave_model", { model_id: modelId });
      socket.disconnect();
    };
  }, [modelId]);

  return { frame, status };
}
