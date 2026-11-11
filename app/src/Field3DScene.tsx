import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { Sim3DOption, Sim3DScenario } from "./types";
import {
  FPS_MIN_FRAMES,
  FPS_SAMPLE_MS,
  MATURE_HEIGHT,
  SEED,
  type CropKind,
  type QualityTier,
  fpsStats,
  headsVisible,
  rainDropCount,
  seasonGrowth,
  seededRandom,
  showIrrigation,
  toCropKind,
  plantsPerSide,
  waterFillFraction,
} from "./field3d/growth";
import { frameGeometry, grainTexture, plantBody, plantHead, rootTemplate, weedRosette } from "./field3d/geometry";

export interface FrameStats {
  median: number;
  p10: number;
  frames: number;
}

export interface Field3DSceneProps {
  option: Sim3DOption;
  scenario: Sim3DScenario;
  weekIndex: number;
  isDark: boolean;
  quality: QualityTier;
  reducedMotion: boolean;
  /** Called once, after ~2 s of visible rendering, with the measured frame rate. */
  onFrameStats?: (stats: FrameStats) => void;
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

const SOIL_DEPTH = 1.6;
const SOIL_WIDTH = 2.4;
const FIELD_HALF = 1.08; // planted area inside the block top
/** Strata are illustrative (not SoilGrids horizons): topsoil, subsoil, substratum. */
const STRATA = [
  { top: 0, bottom: -0.32, light: 0x6b6f8f, dark: 0x3a3f63, opacity: [0.42, 0.5] },
  { top: -0.32, bottom: -0.95, light: 0x3b5a92, dark: 0x1d3560, opacity: [0.26, 0.38] },
  { top: -0.95, bottom: -SOIL_DEPTH, light: 0x23408a, dark: 0x0f2744, opacity: [0.22, 0.34] },
] as const;

interface WeekState {
  option: Sim3DOption;
  scenario: Sim3DScenario;
  weekIndex: number;
}

interface PlantSet {
  body: THREE.InstancedMesh;
  head: THREE.InstancedMesh;
  base: { x: number; z: number; yaw: number; h: number; s: number; lx: number; lz: number }[];
}

interface SceneApi {
  update: (s: WeekState) => void;
}

export function Field3DScene({
  option,
  scenario,
  weekIndex,
  isDark,
  quality,
  reducedMotion,
  onFrameStats,
  onHoverData,
}: Field3DSceneProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const apiRef = useRef<SceneApi | null>(null);
  const latest = useRef<WeekState>({ option, scenario, weekIndex });
  latest.current = { option, scenario, weekIndex };
  const statsCb = useRef(onFrameStats);
  statsCb.current = onFrameStats;

  // Build the scene once per theme / quality tier / motion preference.
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, antialias: quality.antialias, alpha: true, powerPreference: "low-power" });
    } catch {
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, quality.dprCap));
    renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    renderer.shadowMap.autoUpdate = false; // plants only change per week: re-render shadows on change

    const disposables: { dispose: () => void }[] = [];
    const keep = <T extends { dispose: () => void }>(x: T): T => {
      disposables.push(x);
      return x;
    };

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, canvas.clientWidth / Math.max(1, canvas.clientHeight), 0.1, 50);
    camera.position.set(3.4, 3.2, 4.2);
    const target = new THREE.Vector3(0, -0.15, 0);
    camera.lookAt(target);

    // --- Soft sun, sky fill, and the existing blue under-light ---
    scene.add(new THREE.HemisphereLight(isDark ? 0x93c5fd : 0xe0f2fe, isDark ? 0x1e1b2e : 0x4a3f35, isDark ? 0.75 : 0.95));
    scene.add(new THREE.AmbientLight(0xffffff, isDark ? 0.35 : 0.35));
    const sun = new THREE.DirectionalLight(isDark ? 0xfde7c7 : 0xfff1d6, isDark ? 1.2 : 1.6);
    sun.position.set(3.2, 6.5, 2.2);
    sun.castShadow = true;
    sun.shadow.mapSize.set(quality.shadowMapSize, quality.shadowMapSize);
    sun.shadow.radius = 4;
    sun.shadow.bias = -0.0015;
    sun.shadow.normalBias = 0.02;
    const sc = sun.shadow.camera;
    sc.left = sc.bottom = -2;
    sc.right = sc.top = 2;
    sc.near = 1;
    sc.far = 14;
    scene.add(sun);
    const bluePoint = new THREE.PointLight(0x0284c7, isDark ? 1.5 : 0.8, 10);
    bluePoint.position.set(0, -1.0, 0);
    scene.add(bluePoint);

    // --- Layered soil block: translucent blue-tinted glass strata with a fine grain ---
    const grain = grainTexture(SEED);
    if (grain) keep(grain);
    STRATA.forEach((st, i) => {
      const h = st.top - st.bottom;
      const geo = keep(new THREE.BoxGeometry(SOIL_WIDTH, h, SOIL_WIDTH));
      const map = grain ? keep(grain.clone()) : null;
      if (map) {
        map.repeat.set(2.5, Math.max(0.4, h * 1.6));
        map.offset.set(i * 0.37, i * 0.21);
        map.needsUpdate = true;
      }
      const mat = keep(
        new THREE.MeshStandardMaterial({
          color: isDark ? st.dark : st.light,
          map,
          transparent: true,
          opacity: isDark ? st.opacity[1] : st.opacity[0],
          roughness: 0.18,
          metalness: 0.05,
          depthWrite: false,
        }),
      );
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.y = st.bottom + h / 2;
      mesh.renderOrder = 5;
      mesh.receiveShadow = i === 0;
      scene.add(mesh);
      const edges = new THREE.LineSegments(
        keep(new THREE.EdgesGeometry(geo)),
        keep(
          new THREE.LineBasicMaterial({
            color: isDark ? 0x38bdf8 : 0x0284c7,
            transparent: true,
            opacity: i === 0 ? 0.65 : 0.35,
          }),
        ),
      );
      edges.position.y = mesh.position.y;
      edges.renderOrder = 6;
      scene.add(edges);
    });

    // Soil surface that catches soft shadows from the plants.
    const surfaceGeo = keep(new THREE.PlaneGeometry(SOIL_WIDTH, SOIL_WIDTH));
    surfaceGeo.rotateX(-Math.PI / 2);
    const surfaceMap = grain ? keep(grain.clone()) : null;
    if (surfaceMap) {
      surfaceMap.repeat.set(4, 4);
      surfaceMap.needsUpdate = true;
    }
    const surfaceMat = keep(
      new THREE.MeshStandardMaterial({
        color: isDark ? 0x5b5470 : 0x8a7f86,
        map: surfaceMap,
        transparent: true,
        opacity: isDark ? 0.5 : 0.45,
        roughness: 0.9,
        depthWrite: false,
      }),
    );
    const surface = new THREE.Mesh(surfaceGeo, surfaceMat);
    surface.position.y = 0.002;
    surface.receiveShadow = true;
    surface.renderOrder = 6;
    scene.add(surface);

    // --- Water: body up to the fill level, a gently moving surface, and a clear fill line ---
    const inner = SOIL_WIDTH * 0.97;
    const waterBodyGeo = keep(new THREE.BoxGeometry(inner, 1, inner));
    waterBodyGeo.translate(0, 0.5, 0);
    const waterBody = new THREE.Mesh(
      waterBodyGeo,
      keep(
        new THREE.MeshStandardMaterial({
          color: isDark ? 0x0ea5e9 : 0x0284c7,
          transparent: true,
          opacity: isDark ? 0.42 : 0.38,
          roughness: 0.2,
          metalness: 0.1,
          depthWrite: false,
        }),
      ),
    );
    waterBody.position.y = -SOIL_DEPTH;
    waterBody.renderOrder = 2;
    scene.add(waterBody);

    const seg = quality.waterSegments;
    const waterSurfGeo = keep(new THREE.PlaneGeometry(inner, inner, seg, seg));
    waterSurfGeo.rotateX(-Math.PI / 2);
    const waterSurf = new THREE.Mesh(
      waterSurfGeo,
      keep(
        new THREE.MeshStandardMaterial({
          color: isDark ? 0x7dd3fc : 0x38bdf8,
          transparent: true,
          opacity: 0.7,
          roughness: 0.08,
          metalness: 0.25,
          side: THREE.DoubleSide,
          forceSinglePass: true,
          depthWrite: false,
        }),
      ),
    );
    waterSurf.renderOrder = 3;
    scene.add(waterSurf);
    const surfPos = waterSurfGeo.getAttribute("position") as THREE.BufferAttribute;
    const surfBaseX = Float32Array.from({ length: surfPos.count }, (_, i) => surfPos.getX(i));
    const surfBaseZ = Float32Array.from({ length: surfPos.count }, (_, i) => surfPos.getZ(i));

    const fillLine = new THREE.Mesh(
      keep(frameGeometry(SOIL_WIDTH + 0.02, 0.018)),
      keep(new THREE.MeshBasicMaterial({ color: isDark ? 0x7dd3fc : 0x0369a1, transparent: true, opacity: 0.95 })),
    );
    fillLine.renderOrder = 7;
    scene.add(fillLine);

    // --- Roots: one template per crop, replicated on a small grid, scaled to root depth ---
    const rootMat = keep(new THREE.LineBasicMaterial({ color: isDark ? 0xf8fafc : 0xffffff, transparent: true, opacity: 0.6 }));
    const rootMeshes = new Map<CropKind, THREE.LineSegments>();
    const rootsFor = (kind: Exclude<CropKind, "fallow">) => {
      let m = rootMeshes.get(kind);
      if (m) return m;
      const tpl = rootTemplate(kind, SEED + kind.length);
      const src = tpl.getAttribute("position").array as Float32Array;
      const n = quality.rootGrid;
      const out = new Float32Array(src.length * n * n);
      let o = 0;
      for (let a = 0; a < n; a++) {
        for (let b = 0; b < n; b++) {
          const x = -FIELD_HALF * 0.8 + (a + 0.5) * ((FIELD_HALF * 1.6) / n);
          const z = -FIELD_HALF * 0.8 + (b + 0.5) * ((FIELD_HALF * 1.6) / n);
          for (let i = 0; i < src.length; i += 3) {
            out[o++] = src[i] + x;
            out[o++] = src[i + 1];
            out[o++] = src[i + 2] + z;
          }
        }
      }
      tpl.dispose();
      const geo = keep(new THREE.BufferGeometry());
      geo.setAttribute("position", new THREE.BufferAttribute(out, 3));
      m = new THREE.LineSegments(geo, rootMat);
      m.renderOrder = 1;
      m.visible = false;
      rootMeshes.set(kind, m);
      scene.add(m);
      return m;
    };

    // --- Crops: instanced plant bodies and heads (amber translucent; Ks pales them) ---
    // Lambert + single pass: plants are the most numerous surfaces, so they get the cheapest shading.
    const bodyMat = keep(new THREE.MeshLambertMaterial({ transparent: true, side: THREE.DoubleSide, forceSinglePass: true }));
    const headMat = keep(new THREE.MeshLambertMaterial({ transparent: true }));
    const healthy = new THREE.Color(isDark ? 0xf59e0b : 0xb45309);
    const pale = new THREE.Color(isDark ? 0xfef08a : 0xfde68a);
    const headBase = new THREE.Color(isDark ? 0xfbbf24 : 0x92400e);
    const headRipe = new THREE.Color(isDark ? 0xfde68a : 0xa16207);

    const plantSets = new Map<CropKind, PlantSet>();
    const plantsFor = (kind: Exclude<CropKind, "fallow">): PlantSet => {
      let set = plantSets.get(kind);
      if (set) return set;
      const n = plantsPerSide(kind, quality);
      const count = n * n;
      const body = new THREE.InstancedMesh(keep(plantBody(kind)), bodyMat, count);
      const head = new THREE.InstancedMesh(keep(plantHead(kind)), headMat, count);
      const rnd = seededRandom(SEED + count);
      const step = (2 * FIELD_HALF) / n;
      const base: PlantSet["base"] = [];
      for (let r = 0; r < n; r++) {
        for (let c = 0; c < n; c++) {
          base.push({
            // Rows along x (tight in-row jitter), regular spacing between rows along z.
            x: -FIELD_HALF + (c + 0.5) * step + (rnd() - 0.5) * step * 0.5,
            z: -FIELD_HALF + (r + 0.5) * step + (rnd() - 0.5) * step * 0.15,
            yaw: rnd() * Math.PI * 2,
            h: 0.88 + rnd() * 0.2,
            s: 0.85 + rnd() * 0.3,
            lx: (rnd() - 0.5) * 0.12,
            lz: (rnd() - 0.5) * 0.12,
          });
        }
      }
      // Near-to-far from the default camera: the depth test then skips hidden fragments (less overdraw).
      base.sort((p, q) => q.x * 3.4 + q.z * 4.2 - (p.x * 3.4 + p.z * 4.2));
      for (const m of [body, head]) {
        m.castShadow = true;
        m.renderOrder = 8;
        m.visible = false;
        m.frustumCulled = false;
        scene.add(m);
      }
      set = { body, head, base };
      plantSets.set(kind, set);
      return set;
    };

    // Sparse weeds for fallow weeks.
    const weedRnd = seededRandom(SEED + 7);
    const weeds = new THREE.InstancedMesh(
      keep(weedRosette()),
      keep(
        new THREE.MeshLambertMaterial({
          color: isDark ? 0xa3a86b : 0x7c7a3a,
          transparent: true,
          opacity: 0.7,
          side: THREE.DoubleSide,
          forceSinglePass: true,
        }),
      ),
      quality.weeds,
    );
    {
      const m = new THREE.Matrix4();
      const q = new THREE.Quaternion();
      for (let i = 0; i < quality.weeds; i++) {
        const s = 0.7 + weedRnd() * 0.8;
        q.setFromEuler(new THREE.Euler(0, weedRnd() * Math.PI * 2, 0));
        m.compose(
          new THREE.Vector3((weedRnd() * 2 - 1) * FIELD_HALF, 0.004, (weedRnd() * 2 - 1) * FIELD_HALF),
          q,
          new THREE.Vector3(s, s, s),
        );
        weeds.setMatrixAt(i, m);
      }
      weeds.castShadow = true;
      weeds.renderOrder = 8;
      weeds.visible = false;
      scene.add(weeds);
    }

    // --- Weather: rain drops (count ∝ weekly rain) and drip irrigation lines (irrigation > 0) ---
    const dropGeo = keep(new THREE.CylinderGeometry(0.004, 0.004, 0.08, 3));
    const rain = new THREE.InstancedMesh(
      dropGeo,
      keep(new THREE.MeshBasicMaterial({ color: isDark ? 0xbae6fd : 0x0284c7, transparent: true, opacity: 0.65 })),
      quality.maxRainDrops,
    );
    rain.renderOrder = 9;
    rain.frustumCulled = false;
    rain.count = 0;
    scene.add(rain);
    const rainRnd = seededRandom(SEED + 11);
    const drops = Array.from({ length: quality.maxRainDrops }, () => ({
      x: (rainRnd() * 2 - 1) * SOIL_WIDTH * 0.55,
      z: (rainRnd() * 2 - 1) * SOIL_WIDTH * 0.55,
      y: rainRnd() * 2.2,
      v: 2.4 + rainRnd() * 0.8,
    }));
    const dropM = new THREE.Matrix4();
    const placeDrops = () => {
      for (let i = 0; i < rain.count; i++) {
        const d = drops[i];
        dropM.makeTranslation(d.x, 0.05 + d.y, d.z);
        rain.setMatrixAt(i, dropM);
      }
      rain.instanceMatrix.needsUpdate = true;
    };

    const irrigation = new THREE.Group();
    {
      const lines = quality.name === "high" ? 6 : 4;
      const tubeGeo = keep(new THREE.CylinderGeometry(0.013, 0.013, FIELD_HALF * 2, 6));
      tubeGeo.rotateZ(Math.PI / 2);
      const tubeMat = keep(new THREE.MeshStandardMaterial({ color: isDark ? 0x67e8f9 : 0x0891b2, roughness: 0.4 }));
      const emitterGeo = keep(new THREE.SphereGeometry(0.022, 6, 4));
      const emitterMat = keep(
        new THREE.MeshStandardMaterial({ color: isDark ? 0xa5f3fc : 0x22d3ee, transparent: true, opacity: 0.85 }),
      );
      const perLine = quality.name === "high" ? 9 : 6;
      const emitters = new THREE.InstancedMesh(emitterGeo, emitterMat, lines * perLine);
      const m = new THREE.Matrix4();
      for (let l = 0; l < lines; l++) {
        const z = -FIELD_HALF + ((l + 0.5) * 2 * FIELD_HALF) / lines;
        const tube = new THREE.Mesh(tubeGeo, tubeMat);
        tube.position.set(0, 0.016, z);
        tube.renderOrder = 7; // above the translucent soil surface
        irrigation.add(tube);
        for (let e = 0; e < perLine; e++) {
          m.makeTranslation(-FIELD_HALF + ((e + 0.5) * 2 * FIELD_HALF) / perLine, 0.026, z);
          emitters.setMatrixAt(l * perLine + e, m);
        }
      }
      emitters.renderOrder = 7;
      irrigation.add(emitters);
      irrigation.visible = false;
      scene.add(irrigation);
    }

    // --- Per-week update: everything below is driven by pack values ---
    const tmpM = new THREE.Matrix4();
    const tmpQ = new THREE.Quaternion();
    const tmpE = new THREE.Euler();
    const tmpP = new THREE.Vector3();
    const tmpS = new THREE.Vector3();
    let dirty = true;
    let waterLevel = -SOIL_DEPTH;

    const update = ({ option: opt, scenario: scen, weekIndex: wi }: WeekState) => {
      const w = Math.max(0, Math.min(wi, scen.soil_water_mm.length - 1));
      const kind = toCropKind(opt.crops[w]);
      const stage = opt.stages[w] ?? "fallow";
      const canopy = scen.canopy_cover[w] ?? 0;
      const ks = scen.ks[w] ?? 1;
      const rootDepthM = opt.root_depth_m[w] ?? 0;

      // Water fill (soil water / TAW).
      const fill = waterFillFraction(scen.soil_water_mm[w] ?? 0, scen.taw_mm[w] ?? 0);
      const waterH = Math.max(0.02, fill * (SOIL_DEPTH - 0.04));
      waterBody.scale.y = waterH;
      waterLevel = -SOIL_DEPTH + waterH;
      waterSurf.position.y = waterLevel;
      fillLine.position.y = waterLevel;

      // Roots.
      for (const [k, m] of rootMeshes) m.visible = k === kind && rootDepthM > 0.05;
      if (kind !== "fallow" && rootDepthM > 0.05) {
        const m = rootsFor(kind);
        m.visible = true;
        m.scale.y = Math.min(1, rootDepthM / 1.8) * (SOIL_DEPTH - 0.1);
      }

      // Crops.
      for (const [k, set] of plantSets) {
        if (k !== kind) set.body.visible = set.head.visible = false;
      }
      weeds.visible = kind === "fallow";
      if (kind !== "fallow") {
        const growth = seasonGrowth(opt.crops, opt.stages, scen.canopy_cover, w);
        const set = plantsFor(kind);
        const visible = growth > 0.02;
        const height = MATURE_HEIGHT[kind] * Math.max(0.08, growth);
        const spread = 0.55 + 0.45 * growth;
        set.base.forEach((b, i) => {
          tmpE.set(b.lx, b.yaw, b.lz);
          tmpQ.setFromEuler(tmpE);
          tmpP.set(b.x, 0, b.z);
          tmpS.set(spread * b.s, height * b.h, spread * b.s);
          tmpM.compose(tmpP, tmpQ, tmpS);
          set.body.setMatrixAt(i, tmpM);
          set.head.setMatrixAt(i, tmpM);
        });
        set.body.instanceMatrix.needsUpdate = true;
        set.head.instanceMatrix.needsUpdate = true;
        set.body.visible = visible;
        set.head.visible = visible && headsVisible(kind, stage);

        // Colour and opacity exactly as before: amber, paling and fading with water stress (Ks).
        const k01 = Math.max(0, Math.min(1, ks));
        bodyMat.color.copy(pale).lerp(healthy, k01);
        const baseOpacity = isDark ? 0.85 : 0.75;
        const opacity = Math.max(
          0.2,
          Math.min(0.92, (0.28 + 0.72 * k01) * baseOpacity * (0.35 + 0.65 * Math.min(1, canopy * 1.5))),
        );
        bodyMat.opacity = opacity;
        headMat.color.copy(headBase).lerp(headRipe, stage === "late" ? 0.7 : 0);
        headMat.opacity = Math.min(0.95, opacity + 0.05);
      }

      // Weather.
      rain.count = rainDropCount(scen.rain_mm[w] ?? 0, quality.maxRainDrops);
      placeDrops();
      irrigation.visible = showIrrigation(scen.irrigation_mm[w] ?? 0);

      renderer.shadowMap.needsUpdate = true;
      dirty = true;
    };
    // Warm-up: build this rotation's plants and draw one frame with every part visible, so shaders
    // (including shadow ones) compile now and not inside the frame-rate sample.
    for (const c of new Set(latest.current.option.crops.map(toCropKind))) {
      if (c !== "fallow") {
        const set = plantsFor(c);
        set.body.visible = set.head.visible = true;
      }
      const roots = c !== "fallow" ? rootsFor(c) : null;
      if (roots) roots.visible = true;
    }
    weeds.visible = irrigation.visible = true;
    rain.count = 1;
    renderer.shadowMap.needsUpdate = true;
    renderer.render(scene, camera);

    apiRef.current = { update };
    update(latest.current);

    // --- Orbit by drag (same as before) ---
    let isDragging = false;
    let prevX = 0;
    let angle = Math.atan2(camera.position.x, camera.position.z);
    // Step back so the whole block and mature crops stay in frame (more on narrow phone canvases).
    const frameScale = () => (camera.aspect < 1.5 ? 1.18 : 1.1);
    const placeCamera = (dist: number) => {
      const s = frameScale();
      camera.position.set(Math.sin(angle) * dist * s, 3.2 * s, Math.cos(angle) * dist * s);
      camera.lookAt(target);
    };
    let orbitDist = Math.hypot(camera.position.x, camera.position.z);
    placeCamera(orbitDist);
    const onDown = (e: PointerEvent) => {
      isDragging = true;
      prevX = e.clientX;
    };
    const onMove = (e: PointerEvent) => {
      if (!isDragging) return;
      const dx = e.clientX - prevX;
      prevX = e.clientX;
      angle += dx * 0.01;
      orbitDist = 5.6;
      placeCamera(orbitDist);
      dirty = true;
    };
    const onUp = () => {
      isDragging = false;
    };
    canvas.addEventListener("pointerdown", onDown);
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);

    // Pause rendering while the canvas is off screen.
    let onScreen = true;
    const io =
      typeof IntersectionObserver !== "undefined"
        ? new IntersectionObserver((entries) => {
            onScreen = entries.some((e) => e.isIntersecting);
            if (onScreen) dirty = true;
          })
        : null;
    io?.observe(container);

    // --- Render loop with frame-rate sampling for the 2D fallback decision ---
    let raf = 0;
    let last = 0;
    let sampleStart = 0;
    const WARMUP_MS = 500;
    let firstFrame = 0;
    const deltas: number[] = [];
    let sampled = false;
    let prevMotion = 0;
    let t = 0;

    const animate = (now: number) => {
      raf = requestAnimationFrame(animate);
      if (!onScreen) {
        last = 0;
        prevMotion = 0;
        return;
      }

      if (!sampled) {
        if (!firstFrame) firstFrame = now;
        if (last > 0 && now - firstFrame >= WARMUP_MS) {
          if (!sampleStart) sampleStart = now;
          deltas.push(now - last);
          // Need both ~2 s and enough frames, so one start-up stall cannot decide alone.
          if (now - sampleStart >= FPS_SAMPLE_MS && deltas.length >= FPS_MIN_FRAMES) {
            sampled = true;
            const s = fpsStats(deltas);
            container.dataset.fpsMedian = s.median.toFixed(1);
            container.dataset.fpsP10 = s.p10.toFixed(1);
            statsCb.current?.({ ...s, frames: deltas.length });
          }
        }
        last = now;
      }

      if (!reducedMotion) {
        const dt = prevMotion ? Math.min(0.1, (now - prevMotion) / 1000) : 0;
        prevMotion = now;
        t += dt;
        // Gentle water surface movement (decorative; the fill level itself is soil water / TAW).
        for (let i = 0; i < surfPos.count; i++) {
          const x = surfBaseX[i];
          const z = surfBaseZ[i];
          surfPos.setY(i, 0.012 * Math.sin(x * 3.1 + t * 1.3) * Math.cos(z * 2.7 + t * 0.9));
        }
        surfPos.needsUpdate = true;
        waterSurfGeo.computeVertexNormals();
        if (rain.count > 0) {
          for (let i = 0; i < rain.count; i++) {
            const d = drops[i];
            d.y -= d.v * dt;
            if (d.y < 0) d.y += 2.2;
          }
          placeDrops();
        }
        dirty = true;
      }

      // Render continuously while sampling the frame rate (so the fps measure is the real draw
      // rate); afterwards only when something changed (week, drag, resize, water/rain motion).
      if (dirty || !sampled) {
        renderer.render(scene, camera);
        dirty = false;
      }
    };
    raf = requestAnimationFrame(animate);

    const handleResize = () => {
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      if (width === 0 || height === 0) return;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      placeCamera(orbitDist);
      renderer.setSize(width, height, false);
      dirty = true;
    };
    // Follow the canvas's real layout size (it can change after mount without a window resize).
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(handleResize) : null;
    ro?.observe(canvas);
    window.addEventListener("resize", handleResize);

    return () => {
      apiRef.current = null;
      cancelAnimationFrame(raf);
      io?.disconnect();
      ro?.disconnect();
      window.removeEventListener("resize", handleResize);
      canvas.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      for (const set of plantSets.values()) {
        set.body.dispose();
        set.head.dispose();
      }
      weeds.dispose();
      rain.dispose();
      irrigation.traverse((o) => {
        if (o instanceof THREE.InstancedMesh) o.dispose();
      });
      for (const d of disposables) d.dispose();
      sun.shadow.map?.dispose();
      renderer.dispose();
    };
  }, [isDark, quality, reducedMotion]);

  // Per-week update and telemetry for the metric strip.
  useEffect(() => {
    apiRef.current?.update({ option, scenario, weekIndex });

    const w = Math.min(weekIndex, scenario.soil_water_mm.length - 1);
    onHoverData?.({
      week: w,
      crop: option.crops[w] ?? "fallow",
      stage: option.stages[w] ?? "fallow",
      soilWater: scenario.soil_water_mm[w] ?? 0,
      taw: scenario.taw_mm[w] ?? 160,
      canopyCover: scenario.canopy_cover[w] ?? 0,
      ks: scenario.ks[w] ?? 1.0,
      rain: scenario.rain_mm[w] ?? 0,
      irrigation: scenario.irrigation_mm[w] ?? 0,
      rootDepth: option.root_depth_m[w] ?? 0,
    });
  }, [weekIndex, scenario, option, onHoverData]);

  return (
    <div
      ref={containerRef}
      className="field-3d-canvas-container"
      tabIndex={0}
      aria-label={`${option.label} 3D field model`}
    >
      <canvas
        ref={canvasRef}
        className="field-3d-canvas"
        style={{ width: "100%", height: "100%", display: "block" }}
      />
    </div>
  );
}
