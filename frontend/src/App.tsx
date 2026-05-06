import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";
import type { MetricsPayload } from "@shared/contracts";
import { ControlPanel } from "@/components/ControlPanel";
import { MetricPanel } from "@/components/MetricPanel";
import { Viewer3D } from "@/components/Viewer3D";
import { useSimulationSocket } from "@/hooks/useSimulationSocket";
import { apiAssetUrl, optimizeModel, processModel, simulateModel, uploadModel } from "@/lib/api";
import type { ModelEnvelope, ViewerMode } from "@/types";

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [localPreviewUrl, setLocalPreviewUrl] = useState<string>();
  const [model, setModel] = useState<ModelEnvelope | null>(null);
  const [mode, setMode] = useState<ViewerMode>("geometry");
  const [busy, setBusy] = useState({
    uploading: false,
    processing: false,
    simulating: false,
    optimizing: false,
  });
  const [optimization, setOptimization] = useState<{
    baseline_drag: number;
    optimized_drag: number;
    improvement_pct: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const live = useSimulationSocket(model?.model.model_id);
  const deferredFrame = useDeferredValue(live.frame);

  const metrics = useMemo<Partial<MetricsPayload>>(
    () => deferredFrame?.metrics ?? model?.metrics ?? {},
    [deferredFrame, model?.metrics],
  );

  const assetUrl = useMemo(() => {
    if (model?.assets.normalized_url) {
      return apiAssetUrl(model.assets.normalized_url);
    }
    if (model?.assets.upload_url) {
      return apiAssetUrl(model.assets.upload_url);
    }
    return localPreviewUrl;
  }, [localPreviewUrl, model?.assets.normalized_url, model?.assets.upload_url]);

  const assetFormat = useMemo(() => {
    if (model?.assets.normalized_url) {
      return model.assets.normalized_url.split(".").pop()?.toLowerCase();
    }
    if (model?.model.format) {
      return model.model.format;
    }
    return selectedFile?.name.split(".").pop()?.toLowerCase();
  }, [model?.model.format, selectedFile?.name]);

  const setBusyState = (key: keyof typeof busy, value: boolean) => {
    setBusy((current) => ({ ...current, [key]: value }));
  };

  useEffect(() => {
    return () => {
      if (localPreviewUrl) {
        URL.revokeObjectURL(localPreviewUrl);
      }
    };
  }, [localPreviewUrl]);

  const handleFileChange = (file: File | null) => {
    setSelectedFile(file);
    setError(null);
    if (!file) {
      setLocalPreviewUrl(undefined);
      return;
    }
    setLocalPreviewUrl(URL.createObjectURL(file));
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      return;
    }
    try {
      setBusyState("uploading", true);
      setError(null);
      const response = await uploadModel(selectedFile);
      startTransition(() => {
        setModel(response);
      });
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed");
    } finally {
      setBusyState("uploading", false);
    }
  };

  const handleProcess = async () => {
    if (!model) {
      return;
    }
    try {
      setBusyState("processing", true);
      setError(null);
      const response = await processModel(model.model.model_id);
      startTransition(() => {
        setModel(response);
      });
    } catch (processError) {
      setError(processError instanceof Error ? processError.message : "Processing failed");
    } finally {
      setBusyState("processing", false);
    }
  };

  const handleSimulate = async () => {
    if (!model) {
      return;
    }
    try {
      setBusyState("simulating", true);
      setError(null);
      await simulateModel(model.model.model_id, 18);
    } catch (simulationError) {
      setError(simulationError instanceof Error ? simulationError.message : "Simulation failed");
    } finally {
      setBusyState("simulating", false);
    }
  };

  const handleOptimize = async () => {
    if (!model) {
      return;
    }
    try {
      setBusyState("optimizing", true);
      setError(null);
      const response = await optimizeModel(model.model.model_id, 8);
      startTransition(() => {
        setOptimization({
          baseline_drag: response.baseline_drag,
          optimized_drag: response.optimized_drag,
          improvement_pct: response.improvement_pct,
        });
        setModel(response.optimized_model);
        setMode("optimization");
      });
    } catch (optimizationError) {
      setError(optimizationError instanceof Error ? optimizationError.message : "Optimization failed");
    } finally {
      setBusyState("optimizing", false);
    }
  };

  return (
    <main className="grid min-h-screen grid-cols-1 gap-4 p-4 xl:grid-cols-[320px_minmax(0,1fr)_300px]">
      <ControlPanel
        model={model}
        selectedFile={selectedFile}
        mode={mode}
        socketStatus={live.status}
        busy={busy}
        onFileChange={handleFileChange}
        onUpload={handleUpload}
        onProcess={handleProcess}
        onSimulate={handleSimulate}
        onOptimize={handleOptimize}
        onModeChange={setMode}
      />

      <section className="flex min-h-[70vh] flex-col gap-4">
        <Viewer3D assetUrl={assetUrl} assetFormat={assetFormat} mode={mode} frame={deferredFrame} />
        <div className="panel-sheen rounded-[28px] border border-white/10 px-5 py-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-[0.22em] text-paper/55">
              {model?.model.filename ?? "No model loaded"}
            </span>
            <span className="rounded-full border border-neon/20 bg-neon/10 px-3 py-1 text-xs uppercase tracking-[0.22em] text-neon">
              {deferredFrame ? `Frame ${deferredFrame.step}/${deferredFrame.total_steps}` : "Idle"}
            </span>
            <span className="rounded-full border border-frost/20 bg-frost/10 px-3 py-1 text-xs uppercase tracking-[0.22em] text-frost">
              {deferredFrame?.mode ?? "geometry"}
            </span>
          </div>
          <p className="mt-3 text-sm leading-6 text-paper/70">
            Geometry is normalized to the solver domain, while pressure, streamline, and drag overlays are rendered from
            the live streamed surrogate field.
          </p>
          {error ? <p className="mt-3 text-sm text-ember">{error}</p> : null}
        </div>
      </section>

      <MetricPanel metrics={metrics} optimization={optimization} />
    </main>
  );
}

export default App;
