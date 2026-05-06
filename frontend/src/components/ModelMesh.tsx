import { useMemo } from "react";
import { useLoader } from "@react-three/fiber";
import { Mesh, MeshStandardMaterial, type Group, type Material } from "three";
import { GLTFLoader, OBJLoader, STLLoader } from "three-stdlib";

type Props = {
  url?: string;
  format?: string;
  opacity?: number;
  wireframe?: boolean;
};

function PlaceholderMesh() {
  return (
    <mesh>
      <icosahedronGeometry args={[0.55, 1]} />
      <meshStandardMaterial color="#6bf1c7" metalness={0.15} roughness={0.28} wireframe />
    </mesh>
  );
}

function StlMesh({ url, opacity = 1, wireframe = false }: Required<Pick<Props, "url">> & Props) {
  const geometry = useLoader(STLLoader, url);
  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial
        color="#f3efe7"
        transparent={opacity < 1}
        opacity={opacity}
        metalness={0.18}
        roughness={0.38}
        wireframe={wireframe}
      />
    </mesh>
  );
}

function ObjMesh({ url, opacity = 1, wireframe = false }: Required<Pick<Props, "url">> & Props) {
  const object = useLoader(OBJLoader, url);
  const scene = useMemo(() => {
    const cloned = object.clone() as Group;
    cloned.traverse((child) => {
      if ("isMesh" in child && child.isMesh) {
        (child as Mesh).material = new MeshStandardMaterial({
          color: "#f3efe7",
          transparent: opacity < 1,
          opacity,
          metalness: 0.18,
          roughness: 0.38,
          wireframe,
        }) as Material;
      }
    });
    return cloned;
  }, [object, opacity, wireframe]);

  return <primitive object={scene} />;
}

function GltfMesh({ url, opacity = 1, wireframe = false }: Required<Pick<Props, "url">> & Props) {
  const gltf = useLoader(GLTFLoader, url);
  const scene = useMemo(() => {
    const cloned = gltf.scene.clone() as Group;
    cloned.traverse((child) => {
      if ("isMesh" in child && child.isMesh) {
        (child as Mesh).material = new MeshStandardMaterial({
          color: "#f3efe7",
          transparent: opacity < 1,
          opacity,
          metalness: 0.18,
          roughness: 0.38,
          wireframe,
        }) as Material;
      }
    });
    return cloned;
  }, [gltf.scene, opacity, wireframe]);

  return <primitive object={scene} />;
}

export function ModelMesh({ url, format, opacity = 1, wireframe = false }: Props) {
  if (!url || !format) {
    return <PlaceholderMesh />;
  }

  if (format.toLowerCase() === "stl") {
    return <StlMesh url={url} opacity={opacity} wireframe={wireframe} />;
  }

  if (["glb", "gltf"].includes(format.toLowerCase())) {
    return <GltfMesh url={url} opacity={opacity} wireframe={wireframe} />;
  }

  return <ObjMesh url={url} opacity={opacity} wireframe={wireframe} />;
}
