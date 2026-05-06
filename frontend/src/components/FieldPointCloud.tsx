import { useMemo } from "react";
import type { TensorPreview } from "@shared/contracts";

type Props = {
  field?: TensorPreview;
  palette: "pressure" | "drag";
};

function resolveColor(value: number, palette: "pressure" | "drag") {
  if (palette === "drag") {
    return [1, 0.3 + value * 0.5, 0.18];
  }
  return [0.25 + value * 0.75, 0.4 + value * 0.4, 1 - value * 0.6];
}

export function FieldPointCloud({ field, palette }: Props) {
  const { positions, colors } = useMemo(() => {
    if (!field || field.shape.length < 5) {
      return { positions: new Float32Array(), colors: new Float32Array() };
    }

    const [, channels, sizeX, sizeY, sizeZ] = field.shape;
    const positionsBuffer: number[] = [];
    const colorsBuffer: number[] = [];
    const threshold = palette === "drag" ? 0.15 : 0.08;
    const voxelSize = 2 / Math.max(sizeX - 1, 1);

    for (let x = 0; x < sizeX; x += 1) {
      for (let y = 0; y < sizeY; y += 1) {
        for (let z = 0; z < sizeZ; z += 1) {
          const index = (((0 * channels + 0) * sizeX + x) * sizeY + y) * sizeZ + z;
          const value = field.data[index] ?? 0;
          if (value < threshold) {
            continue;
          }
          const px = -1 + x * voxelSize;
          const py = -1 + y * voxelSize;
          const pz = -1 + z * voxelSize;
          positionsBuffer.push(px, py, pz);
          colorsBuffer.push(...resolveColor(Math.min(1, value), palette));
        }
      }
    }

    return {
      positions: new Float32Array(positionsBuffer),
      colors: new Float32Array(colorsBuffer),
    };
  }, [field, palette]);

  if (positions.length === 0) {
    return null;
  }

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={positions.length / 3} array={positions} itemSize={3} />
        <bufferAttribute attach="attributes-color" count={colors.length / 3} array={colors} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={0.055} vertexColors transparent opacity={0.85} sizeAttenuation />
    </points>
  );
}

