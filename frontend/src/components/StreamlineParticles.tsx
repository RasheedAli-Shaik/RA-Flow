import { useFrame } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import { useMemo, useRef } from "react";
import type { Points } from "three";
import type { StreamlinePath } from "@shared/contracts";

type Props = {
  streamlines: StreamlinePath[];
};

export function StreamlineParticles({ streamlines }: Props) {
  const pointsRef = useRef<Points>(null);

  const data = useMemo(() => {
    const particlePositions = new Float32Array(streamlines.length * 3);
    const colors = new Float32Array(streamlines.length * 3);
    streamlines.forEach((path, index) => {
      colors[index * 3] = 0.42;
      colors[index * 3 + 1] = 0.95;
      colors[index * 3 + 2] = 0.78;
      const [x, y, z] = path.points[0] ?? [0, 0, 0];
      particlePositions.set([x, y, z], index * 3);
    });
    return {
      particlePositions,
      colors,
      paths: streamlines.map((streamline) => streamline.points),
    };
  }, [streamlines]);

  useFrame(({ clock }) => {
    const attribute = pointsRef.current?.geometry.getAttribute("position");
    if (!attribute) {
      return;
    }
    data.paths.forEach((path, index) => {
      if (path.length < 2) {
        return;
      }
      const t = (clock.elapsedTime * 0.25 * (1 + (index % 4) * 0.15)) % 1;
      const scaled = t * (path.length - 1);
      const from = Math.floor(scaled);
      const to = Math.min(path.length - 1, from + 1);
      const blend = scaled - from;
      const a = path[from];
      const b = path[to];
      const position = [
        a[0] + (b[0] - a[0]) * blend,
        a[1] + (b[1] - a[1]) * blend,
        a[2] + (b[2] - a[2]) * blend,
      ];
      attribute.setXYZ(index, position[0], position[1], position[2]);
    });
    attribute.needsUpdate = true;
  });

  if (!streamlines.length) {
    return null;
  }

  return (
    <>
      {streamlines.map((streamline, index) => (
        <Line
          key={`${index}-${streamline.points.length}`}
          points={streamline.points as [number, number, number][]}
          color={index % 2 === 0 ? "#6bf1c7" : "#9dd8ff"}
          lineWidth={1.2}
          transparent
          opacity={0.72}
        />
      ))}
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={data.particlePositions.length / 3}
            array={data.particlePositions}
            itemSize={3}
          />
          <bufferAttribute attach="attributes-color" count={data.colors.length / 3} array={data.colors} itemSize={3} />
        </bufferGeometry>
        <pointsMaterial size={0.085} vertexColors transparent opacity={0.95} />
      </points>
    </>
  );
}
