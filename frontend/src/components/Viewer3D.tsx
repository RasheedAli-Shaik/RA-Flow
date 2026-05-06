import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { Bounds, OrbitControls, PerspectiveCamera } from "@react-three/drei";
import type { SimulationFrame } from "@shared/contracts";
import type { ViewerMode } from "@/types";
import { FieldPointCloud } from "./FieldPointCloud";
import { ModelMesh } from "./ModelMesh";
import { StreamlineParticles } from "./StreamlineParticles";

type Props = {
  assetUrl?: string;
  assetFormat?: string;
  mode: ViewerMode;
  frame: SimulationFrame | null;
};

function Scene({ assetUrl, assetFormat, mode, frame }: Props) {
  return (
    <>
      <ambientLight intensity={0.7} />
      <directionalLight position={[2, 3, 4]} intensity={1.2} color="#f3efe7" />
      <directionalLight position={[-4, -1, -2]} intensity={0.6} color="#9dd8ff" />

      <Bounds fit clip observe margin={1.35}>
        <group rotation={[0.15, 0.55, 0]}>
          <ModelMesh
            url={assetUrl}
            format={assetFormat}
            opacity={mode === "geometry" ? 1 : 0.18}
            wireframe={mode === "streamlines"}
          />
          {mode === "pressure" ? <FieldPointCloud field={frame?.pressure_field} palette="pressure" /> : null}
          {mode === "optimization" ? <FieldPointCloud field={frame?.drag_map} palette="drag" /> : null}
          {mode === "streamlines" || mode === "pressure" ? (
            <StreamlineParticles streamlines={frame?.streamlines ?? []} />
          ) : null}
        </group>
      </Bounds>
      <OrbitControls enablePan enableZoom />
    </>
  );
}

export function Viewer3D(props: Props) {
  return (
    <div className="panel-sheen relative h-full overflow-hidden rounded-[32px] border border-white/10">
      <div className="absolute inset-x-0 top-0 z-10 flex items-center justify-between border-b border-white/10 bg-shell/55 px-5 py-3 text-xs uppercase tracking-[0.28em] text-paper/50">
        <span>Viewport</span>
        <span>{props.mode}</span>
      </div>
      <Canvas className="h-full w-full">
        <PerspectiveCamera makeDefault position={[3.2, 2.2, 3.1]} fov={42} />
        <color attach="background" args={["#091019"]} />
        <fog attach="fog" args={["#091019", 3.2, 8.5]} />
        <Suspense fallback={null}>
          <Scene {...props} />
        </Suspense>
      </Canvas>
    </div>
  );
}
