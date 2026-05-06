import type { ChangeEvent } from "react";
import type { ModelEnvelope, SocketStatus, ViewerMode } from "@/types";
import { ModeToggle } from "./ModeToggle";

type Props = {
  model: ModelEnvelope | null;
  selectedFile: File | null;
  mode: ViewerMode;
  socketStatus: SocketStatus;
  busy: {
    uploading: boolean;
    processing: boolean;
    simulating: boolean;
    optimizing: boolean;
  };
  onFileChange: (file: File | null) => void;
  onUpload: () => Promise<void>;
  onProcess: () => Promise<void>;
  onSimulate: () => Promise<void>;
  onOptimize: () => Promise<void>;
  onModeChange: (mode: ViewerMode) => void;
};

export function ControlPanel({
  model,
  selectedFile,
  mode,
  socketStatus,
  busy,
  onFileChange,
  onUpload,
  onProcess,
  onSimulate,
  onOptimize,
  onModeChange,
}: Props) {
  const handleFile = (event: ChangeEvent<HTMLInputElement>) => {
    onFileChange(event.target.files?.[0] ?? null);
  };

  return (
    <aside className="panel-sheen flex h-full flex-col gap-6 rounded-[28px] border border-white/10 p-5 shadow-glow">
      <div>
        <p className="text-xs uppercase tracking-[0.35em] text-frost/70">RA-Flow v2</p>
        <h1 className="mt-3 font-display text-3xl font-bold text-paper">Aerodynamic Intelligence Lab</h1>
        <p className="mt-3 text-sm leading-6 text-paper/70">
          Upload a mesh, voxelize it, stream surrogate flow fields, and push a drag-aware optimization pass.
        </p>
      </div>

      <section className="space-y-3">
        <label className="block text-xs uppercase tracking-[0.25em] text-paper/50">Geometry Upload</label>
        <div className="rounded-3xl border border-dashed border-white/15 bg-white/5 p-4">
          <input
            type="file"
            accept=".stl,.obj,.glb,.gltf,.step,.stp"
            onChange={handleFile}
            className="w-full text-sm text-paper/80 file:mr-4 file:rounded-full file:border-0 file:bg-ember file:px-4 file:py-2 file:font-semibold file:text-shell"
          />
          <p className="mt-3 text-xs text-paper/55">
            {selectedFile ? selectedFile.name : model?.model.filename ?? "Select STL or OBJ geometry"}
          </p>
        </div>
        <button
          type="button"
          onClick={onUpload}
          disabled={!selectedFile || busy.uploading}
          className="w-full rounded-2xl bg-ember px-4 py-3 font-semibold text-shell transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy.uploading ? "Uploading..." : "Upload Geometry"}
        </button>
      </section>

      <section className="space-y-3">
        <label className="block text-xs uppercase tracking-[0.25em] text-paper/50">Simulation Views</label>
        <ModeToggle mode={mode} onChange={onModeChange} />
      </section>

      <section className="space-y-3">
        <label className="block text-xs uppercase tracking-[0.25em] text-paper/50">Pipeline Controls</label>
        <div className="grid gap-3">
          <button
            type="button"
            onClick={onProcess}
            disabled={!model || busy.processing}
            className="rounded-2xl border border-frost/25 bg-frost/10 px-4 py-3 text-left font-semibold text-frost transition hover:border-frost/60 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy.processing ? "Processing geometry..." : "Process Geometry"}
          </button>
          <button
            type="button"
            onClick={onSimulate}
            disabled={!model || busy.simulating}
            className="rounded-2xl border border-neon/25 bg-neon/10 px-4 py-3 text-left font-semibold text-neon transition hover:border-neon/60 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy.simulating ? "Streaming simulation..." : "Run Simulation"}
          </button>
          <button
            type="button"
            onClick={onOptimize}
            disabled={!model || busy.optimizing}
            className="rounded-2xl border border-ember/25 bg-ember/10 px-4 py-3 text-left font-semibold text-ember transition hover:border-ember/60 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy.optimizing ? "Vibe optimizing..." : "Vibe Optimize"}
          </button>
        </div>
      </section>

      <section className="mt-auto rounded-3xl border border-white/10 bg-shell/60 p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs uppercase tracking-[0.25em] text-paper/45">Realtime</span>
          <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-paper/70">
            {socketStatus.status}
          </span>
        </div>
        <p className="mt-3 text-sm text-paper/70">
          Model: <span className="font-semibold text-paper">{model?.model.model_id ?? "none"}</span>
        </p>
      </section>
    </aside>
  );
}
