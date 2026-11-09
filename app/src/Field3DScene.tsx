import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { Sim3DOption, Sim3DScenario } from "./types";

export interface Field3DSceneProps {
  option: Sim3DOption;
  scenario: Sim3DScenario;
  weekIndex: number;
  isDark: boolean;
  onHoverData?: (data: {
    week: number;
    crop: string;
    stage: string;
    soilWater: number;
    taw: number;
    canopyCover: number;
    ks: number;
    rain: number;
    irrigation: number;
    rootDepth: number;
  } | null) => void;
}

export function Field3DScene({
  option,
  scenario,
  weekIndex,
  isDark,
  onHoverData,
}: Field3DSceneProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const reqIdRef = useRef<number | null>(null);

  // Mesh refs for smooth per-week updates without recreating the scene
  const waterMeshRef = useRef<THREE.Mesh | null>(null);
  const rootsGroupRef = useRef<THREE.Group | null>(null);
  const cropsGroupRef = useRef<THREE.Group | null>(null);

  const soilDepth = 1.6;
  const soilWidth = 2.4;

  // Initialize Three.js scene once
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Check WebGL availability
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    } catch {
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    rendererRef.current = renderer;

    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(
      38,
      canvas.clientWidth / canvas.clientHeight,
      0.1,
      50
    );
    camera.position.set(3.4, 3.2, 4.2);
    camera.lookAt(0, -0.2, 0);

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, isDark ? 0.9 : 1.1);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 1.4);
    dirLight.position.set(5, 8, 5);
    scene.add(dirLight);

    const bluePoint = new THREE.PointLight(0x0284c7, isDark ? 1.5 : 0.8, 10);
    bluePoint.position.set(0, -1.0, 0);
    scene.add(bluePoint);

    // 1. Soil Block (translucent blue glass look)
    const soilGeo = new THREE.BoxGeometry(soilWidth, soilDepth, soilWidth);
    const soilMat = new THREE.MeshStandardMaterial({
      color: isDark ? 0x0f2744 : 0x1e3a8a,
      transparent: true,
      opacity: isDark ? 0.35 : 0.22,
      roughness: 0.3,
      metalness: 0.1,
    });
    const soilMesh = new THREE.Mesh(soilGeo, soilMat);
    soilMesh.position.y = -soilDepth / 2;
    scene.add(soilMesh);

    // Soil edges outline
    const soilEdgesGeo = new THREE.EdgesGeometry(soilGeo);
    const soilEdgesMat = new THREE.LineBasicMaterial({
      color: isDark ? 0x38bdf8 : 0x0284c7,
      transparent: true,
      opacity: 0.6,
    });
    const soilEdges = new THREE.LineSegments(soilEdgesGeo, soilEdgesMat);
    soilEdges.position.y = -soilDepth / 2;
    scene.add(soilEdges);

    // 2. Inner Water Layer (deeper vibrant blue)
    const waterGeo = new THREE.BoxGeometry(soilWidth * 0.98, 0.05, soilWidth * 0.98);
    const waterMat = new THREE.MeshStandardMaterial({
      color: isDark ? 0x0ea5e9 : 0x0284c7,
      transparent: true,
      opacity: 0.75,
      roughness: 0.15,
      metalness: 0.2,
    });
    const waterMesh = new THREE.Mesh(waterGeo, waterMat);
    waterMesh.position.y = -soilDepth + 0.025;
    scene.add(waterMesh);
    waterMeshRef.current = waterMesh;

    // 3. Roots Group
    const rootsGroup = new THREE.Group();
    scene.add(rootsGroup);
    rootsGroupRef.current = rootsGroup;

    // 4. Crops Group
    const cropsGroup = new THREE.Group();
    scene.add(cropsGroup);
    cropsGroupRef.current = cropsGroup;

    // Render loop with slight subtle turntable rotation on drag or slow idle
    let isDragging = false;
    let prevX = 0;
    let angle = 0;

    const handlePointerDown = (e: PointerEvent) => {
      isDragging = true;
      prevX = e.clientX;
    };
    const handlePointerMove = (e: PointerEvent) => {
      if (!isDragging) return;
      const dx = e.clientX - prevX;
      prevX = e.clientX;
      angle += dx * 0.01;
      const dist = 5.6;
      camera.position.x = Math.sin(angle) * dist;
      camera.position.z = Math.cos(angle) * dist;
      camera.lookAt(0, -0.2, 0);
    };
    const handlePointerUp = () => {
      isDragging = false;
    };

    canvas.addEventListener("pointerdown", handlePointerDown);
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);

    const animate = () => {
      reqIdRef.current = requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!canvas || !rendererRef.current) return;
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      if (width === 0 || height === 0) return;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      rendererRef.current.setSize(width, height, false);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      canvas.removeEventListener("pointerdown", handlePointerDown);
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      if (reqIdRef.current) cancelAnimationFrame(reqIdRef.current);
      renderer.dispose();
      soilGeo.dispose();
      soilMat.dispose();
      soilEdgesGeo.dispose();
      soilEdgesMat.dispose();
      waterGeo.dispose();
      waterMat.dispose();
    };
  }, [isDark]);

  // Update water level, roots, and crops whenever weekIndex or scenario changes
  useEffect(() => {
    const w = Math.min(weekIndex, scenario.soil_water_mm.length - 1);
    const sw = scenario.soil_water_mm[w] ?? 0;
    const taw = scenario.taw_mm[w] ?? 160;
    const canopy = scenario.canopy_cover[w] ?? 0;
    const ks = scenario.ks[w] ?? 1.0;
    const rain = scenario.rain_mm[w] ?? 0;
    const irr = scenario.irrigation_mm[w] ?? 0;
    const cropName = option.crops[w] ?? "fallow";
    const stage = option.stages[w] ?? "fallow";
    const rootDepthM = option.root_depth_m[w] ?? 0;

    // Report hover data to parent
    if (onHoverData) {
      onHoverData({
        week: w,
        crop: cropName,
        stage,
        soilWater: sw,
        taw,
        canopyCover: canopy,
        ks,
        rain,
        irrigation: irr,
        rootDepth: rootDepthM,
      });
    }

    // 1. Update Water Level inside soil
    if (waterMeshRef.current) {
      const fraction = Math.max(0.01, Math.min(1.0, sw / (taw || 1)));
      const waterHeight = Math.max(0.04, fraction * (soilDepth - 0.05));
      waterMeshRef.current.scale.set(1, waterHeight / 0.05, 1);
      waterMeshRef.current.position.y = -soilDepth + waterHeight / 2;
    }

    // 2. Update Roots in soil
    if (rootsGroupRef.current) {
      // Clear previous root children
      while (rootsGroupRef.current.children.length > 0) {
        const c = rootsGroupRef.current.children[0];
        rootsGroupRef.current.remove(c);
        if (c instanceof THREE.LineSegments) {
          c.geometry.dispose();
          if (Array.isArray(c.material)) c.material.forEach((m) => m.dispose());
          else c.material.dispose();
        }
      }

      if (rootDepthM > 0.05 && cropName !== "fallow") {
        // Build stylized roots growing downward
        const rootFrac = Math.min(1.0, rootDepthM / 1.8);
        const maxRootY = rootFrac * (soilDepth - 0.1);
        const points: THREE.Vector3[] = [];

        // 3x3 plant grid on field
        const offsets = [-0.65, 0, 0.65];
        for (const x of offsets) {
          for (const z of offsets) {
            // Main tap root
            points.push(new THREE.Vector3(x, 0, z));
            points.push(new THREE.Vector3(x, -maxRootY, z));

            // 3 lateral branch roots
            if (maxRootY > 0.2) {
              points.push(new THREE.Vector3(x, -maxRootY * 0.4, z));
              points.push(new THREE.Vector3(x + 0.18, -maxRootY * 0.7, z + 0.12));

              points.push(new THREE.Vector3(x, -maxRootY * 0.5, z));
              points.push(new THREE.Vector3(x - 0.15, -maxRootY * 0.8, z - 0.14));

              points.push(new THREE.Vector3(x, -maxRootY * 0.6, z));
              points.push(new THREE.Vector3(x + 0.12, -maxRootY * 0.9, z - 0.15));
            }
          }
        }

        const rootGeo = new THREE.BufferGeometry().setFromPoints(points);
        const rootMat = new THREE.LineBasicMaterial({
          color: isDark ? 0xf8fafc : 0xffffff,
          transparent: true,
          opacity: 0.65,
        });
        const rootsMesh = new THREE.LineSegments(rootGeo, rootMat);
        rootsGroupRef.current.add(rootsMesh);
      }
    }

    // 3. Update Crops on field surface (y >= 0)
    if (cropsGroupRef.current) {
      // Clear previous crop meshes
      while (cropsGroupRef.current.children.length > 0) {
        const c = cropsGroupRef.current.children[0];
        cropsGroupRef.current.remove(c);
        if (c instanceof THREE.Mesh) {
          c.geometry.dispose();
          if (Array.isArray(c.material)) c.material.forEach((m) => m.dispose());
          else c.material.dispose();
        } else if (c instanceof THREE.Group) {
          c.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.geometry.dispose();
              if (Array.isArray(child.material)) child.material.forEach((m) => m.dispose());
              else child.material.dispose();
            }
          });
        }
      }

      if (cropName !== "fallow" && canopy > 0.05) {
        // Hologram amber crop: height reflects canopy, opacity reflects stress & density
        const cropHeight = Math.max(0.1, canopy * 1.1);
        const cropOpacity = Math.max(0.2, Math.min(0.9, ks * (0.35 + 0.65 * canopy)));
        const amberColor = isDark ? 0xf59e0b : 0xd97706;

        const stalkMat = new THREE.MeshStandardMaterial({
          color: amberColor,
          transparent: true,
          opacity: cropOpacity,
          roughness: 0.4,
        });

        const leafMat = new THREE.MeshStandardMaterial({
          color: amberColor,
          transparent: true,
          opacity: cropOpacity * 0.85,
          side: THREE.DoubleSide,
        });

        const headMat = new THREE.MeshStandardMaterial({
          color: isDark ? 0xfbbf24 : 0xb45309,
          transparent: true,
          opacity: cropOpacity,
        });

        const offsets = [-0.65, 0, 0.65];
        for (const x of offsets) {
          for (const z of offsets) {
            const plantGroup = new THREE.Group();
            plantGroup.position.set(x, 0, z);

            // Stalk
            const stalkGeo = new THREE.CylinderGeometry(0.015, 0.03, cropHeight, 6);
            const stalk = new THREE.Mesh(stalkGeo, stalkMat);
            stalk.position.y = cropHeight / 2;
            plantGroup.add(stalk);

            // Stylized leaves
            const leafGeo = new THREE.ConeGeometry(0.12, cropHeight * 0.45, 4);
            const leaf1 = new THREE.Mesh(leafGeo, leafMat);
            leaf1.rotation.z = Math.PI / 4;
            leaf1.position.set(0.1, cropHeight * 0.4, 0);
            plantGroup.add(leaf1);

            const leaf2 = new THREE.Mesh(leafGeo, leafMat);
            leaf2.rotation.z = -Math.PI / 4;
            leaf2.position.set(-0.1, cropHeight * 0.5, 0);
            plantGroup.add(leaf2);

            // Seed/Grain Head on top
            if (cropHeight > 0.3) {
              const headGeo =
                cropName === "winter_wheat"
                  ? new THREE.CylinderGeometry(0.03, 0.03, cropHeight * 0.25, 6)
                  : new THREE.SphereGeometry(0.07, 6, 6);
              const head = new THREE.Mesh(headGeo, headMat);
              head.position.y = cropHeight + 0.05;
              plantGroup.add(head);
            }

            cropsGroupRef.current.add(plantGroup);
          }
        }
      }
    }
  }, [weekIndex, scenario, option, isDark, onHoverData]);

  return (
    <div className="field-3d-canvas-container" tabIndex={0} aria-label={`${option.label} 3D field model`}>
      <canvas
        ref={canvasRef}
        className="field-3d-canvas"
        style={{ width: "100%", height: "100%", display: "block" }}
      />
    </div>
  );
}
