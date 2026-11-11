// Farm view of Field in 3D: an isometric low-poly farm with two fenced plots side by side,
// "Current rotation" and the other rotation, showing the SAME field over the same weeks and
// weather. Plot contents follow `field3d/farm.ts` (pack / replay values only); the barn, trees,
// pond, fences and paths are scenery, not data (labelled in the view). All geometry is
// procedural (no downloaded models). Rendering mirrors Field3DScene: capped pixel ratio and
// instance counts per quality tier, frame-rate sampling for the 2D fallback, paused off screen.
import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { FrameStats } from "./Field3DScene";
import { plantBody, plantHead, weedRosette } from "./field3d/geometry";
import { type PlotWeek, plotWeek, weekLook } from "./field3d/farm";
import {
  FPS_MIN_FRAMES,
  FPS_SAMPLE_MS,
  MATURE_HEIGHT,
  SEED,
  type QualityTier,
  fpsStats,
  plantsPerSide,
  seededRandom,
} from "./field3d/growth";
import type { Sim3DOption, Sim3DScenario } from "./types";

export interface FarmSceneProps {
  plots: [{ option: Sim3DOption; scenario: Sim3DScenario }, { option: Sim3DOption; scenario: Sim3DScenario }];
  weekIndex: number;
  month: number;
  isDark: boolean;
  quality: QualityTier;
  reducedMotion: boolean;
  onFrameStats?: (s: FrameStats) => void;
}

type CropKey = "maize" | "sorghum" | "winter_wheat";
const CROPS: CropKey[] = ["maize", "sorghum", "winter_wheat"];
// Plot centres on the screen-horizontal diagonal (x - z) of the isometric view: left, right.
const PLOT_POS: [number, number][] = [
  [-1.5, 1.5],
  [1.5, -1.5],
];
const PLOT_HALF = 1.15; // soil bed half-size
const PLANT_HALF = 1.0; // planted area half-size
const PLANT_SCALE = 0.62; // plants are drawn smaller than in the glass view (display only)
const AREA = { x: 5.2, z: 5.2 }; // ground half-size

interface PlotApi {
  update: (p: PlotWeek) => void;
}

/** Plant colours (display only): green, paling with water stress, straw when ripe. */
function plantColours(isDark: boolean) {
  return {
    healthy: new THREE.Color(isDark ? 0x6fbf4a : 0x4f8f2f),
    pale: new THREE.Color(isDark ? 0xe6dc9a : 0xd8cf86),
    ripe: new THREE.Color(isDark ? 0xe0bf63 : 0xc9a64a),
    head: { maize: new THREE.Color(0xe3c14a), sorghum: new THREE.Color(0xa0522d), winter_wheat: new THREE.Color(0xd6b14a) },
    cover: new THREE.Color(isDark ? 0x7fd06a : 0x5aa845),
    soilDry: new THREE.Color(isDark ? 0x7d5f43 : 0x9a7350),
    soilWet: new THREE.Color(isDark ? 0x3f2e20 : 0x5e4430),
    neutral: new THREE.Color(isDark ? 0x8a9096 : 0x9aa0a6),
  };
}

export function FarmScene({ plots, weekIndex, month, isDark, quality, reducedMotion, onFrameStats }: FarmSceneProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const apiRef = useRef<{ update: () => void } | null>(null);
  const latest = useRef({ plots, weekIndex, month });
  latest.current = { plots, weekIndex, month };
  const statsCb = useRef(onFrameStats);
  statsCb.current = onFrameStats;

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, antialias: quality.antialias, powerPreference: "low-power" });
    } catch {
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, quality.dprCap));
    renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    const shadows = quality.name === "high";
    renderer.shadowMap.enabled = shadows;
    renderer.shadowMap.autoUpdate = false;

    const disposables: { dispose: () => void }[] = [];
    const keep = <T extends { dispose: () => void }>(x: T): T => {
      disposables.push(x);
      return x;
    };
    const col = plantColours(isDark);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(isDark ? 0x1d3a55 : 0x9fd3f2);

    // --- Isometric orthographic camera (fits both plots; wider screens show more scenery) ---
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 60);
    camera.position.set(9, 7.4, 9);
    camera.lookAt(-0.4, 0, -0.4);
    const fit = () => {
      const aspect = canvas.clientWidth / Math.max(1, canvas.clientHeight);
      let hw = 3.9;
      let hh = hw / aspect;
      if (hh < 2.7) {
        hh = 2.7;
        hw = hh * aspect;
      }
      camera.left = -hw;
      camera.right = hw;
      camera.top = hh;
      camera.bottom = -hh;
      camera.updateProjectionMatrix();
    };
    fit();

    scene.add(new THREE.HemisphereLight(isDark ? 0x9cc3e6 : 0xeaf6ff, isDark ? 0x2a3a22 : 0x6b8f4a, isDark ? 0.9 : 1.1));
    const sun = new THREE.DirectionalLight(isDark ? 0xf3e3c3 : 0xfff2d8, isDark ? 1.0 : 1.5);
    sun.position.set(4, 8, 3);
    if (shadows) {
      sun.castShadow = true;
      sun.shadow.mapSize.set(quality.shadowMapSize, quality.shadowMapSize);
      const sc = sun.shadow.camera;
      sc.left = sc.bottom = -4;
      sc.right = sc.top = 4;
      sc.near = 1;
      sc.far = 20;
      sun.shadow.bias = -0.002;
    }
    scene.add(sun);

    const flat = (color: number) => keep(new THREE.MeshLambertMaterial({ color, flatShading: true }));

    // --- Scenery (not data): grass, paths, fences, trees, barn, pond ---
    const grassMat = keep(new THREE.MeshLambertMaterial({ color: 0x7fb55a }));
    const ground = new THREE.Mesh(keep(new THREE.BoxGeometry(AREA.x * 2, 0.2, AREA.z * 2)), grassMat);
    ground.position.y = -0.1;
    ground.receiveShadow = shadows;
    scene.add(ground);

    const pathMat = flat(isDark ? 0x8a7458 : 0xc9b08a);
    const addBox = (w: number, h: number, d: number, x: number, y: number, z: number, mat: THREE.Material, parent: THREE.Object3D = scene) => {
      const m = new THREE.Mesh(keep(new THREE.BoxGeometry(w, h, d)), mat);
      m.position.set(x, y, z);
      parent.add(m);
      return m;
    };
    // a path between the plots (along the x + z diagonal) and one along the front, to the barn
    addBox(0.55, 0.02, AREA.x * 2.6, 0, 0.01, 0, pathMat).rotation.y = Math.PI / 4;
    addBox(0.55, 0.02, AREA.z * 2, -PLOT_HALF - 1.95, 0.011, 0, pathMat);
    addBox(AREA.x * 2, 0.02, 0.55, 0, 0.012, PLOT_HALF + 1.95, pathMat);

    // fences: instanced posts + rails around each plot
    const fenceMat = flat(isDark ? 0xb08a5f : 0x9c7448);
    const postGeo = keep(new THREE.BoxGeometry(0.06, 0.32, 0.06));
    const fh = PLOT_HALF + 0.12;
    const postPos: [number, number][] = [];
    for (const [px, pz] of PLOT_POS) {
      for (let i = 0; i <= 8; i++) {
        const t = -fh + (i * 2 * fh) / 8;
        postPos.push([px + t, pz - fh], [px + t, pz + fh]);
        if (i > 0 && i < 8) postPos.push([px - fh, pz + t], [px + fh, pz + t]);
      }
    }
    const posts = new THREE.InstancedMesh(postGeo, fenceMat, postPos.length);
    const pm = new THREE.Matrix4();
    postPos.forEach(([x, z], i) => posts.setMatrixAt(i, pm.makeTranslation(x, 0.16, z)));
    posts.castShadow = shadows;
    scene.add(posts);
    for (const [px, pz] of PLOT_POS) {
      for (const y of [0.13, 0.26]) {
        addBox(2 * fh, 0.035, 0.03, px, y, pz - fh, fenceMat);
        addBox(2 * fh, 0.035, 0.03, px, y, pz + fh, fenceMat);
        addBox(0.03, 0.035, 2 * fh, px - fh, y, pz, fenceMat);
        addBox(0.03, 0.035, 2 * fh, px + fh, y, pz, fenceMat);
      }
    }

    // trees: low-poly crowns on trunks
    const trunkMat = flat(isDark ? 0x7a5a3c : 0x6e4f33);
    const crownMats = [flat(isDark ? 0x4c8a3c : 0x3f7d36), flat(isDark ? 0x5f9c45 : 0x4f8f3a)];
    const trunkGeo = keep(new THREE.CylinderGeometry(0.06, 0.08, 0.45, 5));
    const crownGeo = keep(new THREE.IcosahedronGeometry(0.42, 0));
    const treeRnd = seededRandom(SEED + 3);
    for (const [x, z] of [[-4.4, 3.4], [-3.4, 4.4], [4.4, -3.9], [3.0, -4.6], [-1.2, -4.2], [-4.3, -0.6], [1.6, 3.9], [4.9, -0.6]] as const) {
      const s = 0.8 + treeRnd() * 0.5;
      const trunk = new THREE.Mesh(trunkGeo, trunkMat);
      trunk.position.set(x, 0.22 * s, z);
      trunk.scale.setScalar(s);
      const crown = new THREE.Mesh(crownGeo, crownMats[Math.floor(treeRnd() * 2)]);
      crown.position.set(x, 0.62 * s, z);
      crown.scale.set(s, s * 1.15, s);
      crown.rotation.y = treeRnd() * Math.PI;
      crown.castShadow = trunk.castShadow = shadows;
      scene.add(trunk, crown);
    }

    // barn: walls, gabled roof, door (generic shapes, own palette)
    const barn = new THREE.Group();
    barn.position.set(-2.4, 0, -2.6);
    barn.rotation.y = 0;
    addBox(1.3, 0.85, 1.0, 0, 0.425, 0, flat(isDark ? 0x9b5a48 : 0xa4553f), barn);
    const roofMat = flat(isDark ? 0x5d6b75 : 0x51606b);
    for (const side of [-1, 1]) {
      const r = addBox(1.42, 0.05, 0.62, 0, 1.03, side * 0.26, roofMat, barn);
      r.rotation.x = side * 0.62;
    }
    const gable = new THREE.Shape([new THREE.Vector2(-0.5, 0), new THREE.Vector2(0.5, 0), new THREE.Vector2(0, 0.4)]);
    const gableGeo = keep(new THREE.ShapeGeometry(gable));
    for (const side of [-1, 1]) {
      const g = new THREE.Mesh(gableGeo, flat(isDark ? 0x9b5a48 : 0xa4553f));
      g.position.set(side * 0.651, 0.85, 0);
      g.rotation.y = (side * Math.PI) / 2;
      barn.add(g);
    }
    addBox(0.02, 0.5, 0.42, 0.66, 0.25, 0, flat(isDark ? 0xe8e2d6 : 0xf3efe6), barn);
    barn.traverse((o) => (o.castShadow = shadows));
    scene.add(barn);

    // pond with a ring of stones
    const pond = new THREE.Mesh(keep(new THREE.CircleGeometry(0.85, 9)), flat(isDark ? 0x2f6f99 : 0x4aa3d6));
    pond.rotation.x = -Math.PI / 2;
    pond.position.set(3.7, 0.015, 0.9);
    pond.scale.set(1.25, 1, 1);
    scene.add(pond);
    const stones = new THREE.InstancedMesh(keep(new THREE.DodecahedronGeometry(0.09, 0)), flat(isDark ? 0x8c9399 : 0xa9b0b5), 14);
    for (let i = 0; i < 14; i++) {
      const a = (i / 14) * Math.PI * 2;
      pm.makeTranslation(3.7 + Math.cos(a) * 1.08, 0.04, 0.9 + Math.sin(a) * 0.88);
      stones.setMatrixAt(i, pm);
    }
    scene.add(stones);

    // --- Plots: soil bed, crops (instanced), cover, neutral slab, sprinkler ---
    const tier: QualityTier = { ...quality, maxPlantInstances: Math.floor(quality.maxPlantInstances / 2) };
    const tmpM = new THREE.Matrix4();
    const tmpQ = new THREE.Quaternion();
    const tmpE = new THREE.Euler();
    const tmpP = new THREE.Vector3();
    const tmpS = new THREE.Vector3();
    const sprays: { group: THREE.Group; on: boolean }[] = [];

    const makePlot = ([px, pz]: [number, number], seed: number): PlotApi => {
      const g = new THREE.Group();
      g.position.set(px, 0, pz);
      scene.add(g);
      const soilMat = keep(new THREE.MeshLambertMaterial({ color: col.soilDry }));
      const soil = addBox(2 * PLOT_HALF, 0.1, 2 * PLOT_HALF, 0, 0.05, 0, soilMat, g);
      soil.receiveShadow = shadows;
      // furrows: thin darker strips (scenery detail on the bed)
      const furrowMat = keep(new THREE.MeshLambertMaterial({ color: col.soilWet, transparent: true, opacity: 0.35 }));
      for (let r = 0; r < 6; r++) addBox(2 * PLANT_HALF, 0.004, 0.05, 0, 0.102, -PLANT_HALF + ((r + 0.5) * 2 * PLANT_HALF) / 6, furrowMat, g);
      const neutral = addBox(2 * PLOT_HALF, 0.03, 2 * PLOT_HALF, 0, 0.115, 0, keep(new THREE.MeshLambertMaterial({ color: col.neutral })), g);
      neutral.visible = false;

      const bodyMat = keep(new THREE.MeshLambertMaterial({ side: THREE.DoubleSide, flatShading: true }));
      const headMat = keep(new THREE.MeshLambertMaterial({ flatShading: true }));
      const sets = new Map<CropKey, { body: THREE.InstancedMesh; head: THREE.InstancedMesh; base: { x: number; z: number; yaw: number; h: number; s: number }[] }>();
      const setFor = (k: CropKey) => {
        let s = sets.get(k);
        if (s) return s;
        const n = plantsPerSide(k, tier);
        const body = new THREE.InstancedMesh(keep(plantBody(k)), bodyMat, n * n);
        const head = new THREE.InstancedMesh(keep(plantHead(k)), headMat, n * n);
        const rnd = seededRandom(seed + n);
        const step = (2 * PLANT_HALF) / n;
        const base: { x: number; z: number; yaw: number; h: number; s: number }[] = [];
        for (let r = 0; r < n; r++)
          for (let c = 0; c < n; c++)
            base.push({
              x: -PLANT_HALF + (c + 0.5) * step + (rnd() - 0.5) * step * 0.4,
              z: -PLANT_HALF + (r + 0.5) * step + (rnd() - 0.5) * step * 0.15,
              yaw: rnd() * Math.PI * 2,
              h: 0.88 + rnd() * 0.2,
              s: 0.85 + rnd() * 0.3,
            });
        for (const m of [body, head]) {
          m.castShadow = shadows;
          m.visible = false;
          m.frustumCulled = false;
          g.add(m);
        }
        s = { body, head, base };
        sets.set(k, s);
        return s;
      };
      const coverN = quality.name === "high" ? 64 : 30;
      const cover = new THREE.InstancedMesh(keep(weedRosette()), keep(new THREE.MeshLambertMaterial({ color: col.cover, side: THREE.DoubleSide })), coverN);
      const cRnd = seededRandom(seed + 9);
      const coverBase = Array.from({ length: coverN }, () => ({ x: (cRnd() * 2 - 1) * PLANT_HALF, z: (cRnd() * 2 - 1) * PLANT_HALF, yaw: cRnd() * 6.28 }));
      cover.visible = false;
      g.add(cover);

      // sprinkler: a post and a ring of spray droplets (animated); shown only when irrigation > 0
      const spray = new THREE.Group();
      addBox(0.04, 0.5, 0.04, 0, 0.35, 0, flat(0x6b7680), spray);
      const dropMat = keep(new THREE.MeshBasicMaterial({ color: isDark ? 0xbae6fd : 0x38a6d9, transparent: true, opacity: 0.8 }));
      const dropGeo = keep(new THREE.SphereGeometry(0.03, 5, 3));
      for (let i = 0; i < 18; i++) {
        const a = (i / 18) * Math.PI * 2;
        const r = 0.25 + (i % 3) * 0.22;
        const d = new THREE.Mesh(dropGeo, dropMat);
        d.position.set(Math.cos(a) * r, 0.6 - (i % 3) * 0.14, Math.sin(a) * r);
        spray.add(d);
      }
      spray.visible = false;
      g.add(spray);
      const sprayRef = { group: spray, on: false };
      sprays.push(sprayRef);

      return {
        update: (p) => {
          soilMat.color.copy(col.soilDry).lerp(col.soilWet, p.wetness);
          neutral.visible = p.kind === "not_simulated";
          sprayRef.on = p.irrigating;
          spray.visible = p.irrigating;
          for (const [k, s] of sets) if (k !== p.kind) s.body.visible = s.head.visible = false;
          cover.visible = p.kind === "cover";
          if (p.kind === "cover") {
            const sc = 1.2 + 2.2 * p.growth;
            coverBase.forEach((b, i) => {
              tmpE.set(0, b.yaw, 0);
              tmpQ.setFromEuler(tmpE);
              cover.setMatrixAt(i, tmpM.compose(tmpP.set(b.x, 0.1, b.z), tmpQ, tmpS.set(sc, sc, sc)));
            });
            cover.instanceMatrix.needsUpdate = true;
          }
          if (p.kind === "maize" || p.kind === "sorghum" || p.kind === "winter_wheat") {
            const s = setFor(p.kind);
            const height = MATURE_HEIGHT[p.kind] * PLANT_SCALE * Math.max(0.08, p.growth);
            const spread = (0.55 + 0.45 * p.growth) * PLANT_SCALE;
            s.base.forEach((b, i) => {
              tmpE.set(0, b.yaw, 0);
              tmpQ.setFromEuler(tmpE);
              tmpM.compose(tmpP.set(b.x, 0.1, b.z), tmpQ, tmpS.set(spread * b.s, height * b.h, spread * b.s));
              s.body.setMatrixAt(i, tmpM);
              s.head.setMatrixAt(i, tmpM);
            });
            s.body.instanceMatrix.needsUpdate = s.head.instanceMatrix.needsUpdate = true;
            s.body.visible = p.growth > 0.02;
            s.head.visible = s.body.visible && p.heads;
            bodyMat.color.copy(p.ripe ? col.ripe : col.healthy).lerp(col.pale, p.stress);
            headMat.color.copy(col.head[p.kind]).lerp(col.pale, p.stress * 0.5);
          }
        },
      };
    };
    const plotApis = PLOT_POS.map((pos, i) => makePlot(pos, SEED + 100 * (i + 1)));

    // --- Rain over the whole farm (count from the week's rain, same weather for both plots) ---
    const rain = new THREE.InstancedMesh(
      keep(new THREE.CylinderGeometry(0.008, 0.008, 0.16, 3)),
      keep(new THREE.MeshBasicMaterial({ color: isDark ? 0xbae6fd : 0x4f8fc0, transparent: true, opacity: 0.6 })),
      quality.maxRainDrops,
    );
    rain.count = 0;
    rain.frustumCulled = false;
    scene.add(rain);
    const rRnd = seededRandom(SEED + 21);
    const drops = Array.from({ length: quality.maxRainDrops }, () => ({
      x: (rRnd() * 2 - 1) * AREA.x * 0.9,
      z: (rRnd() * 2 - 1) * AREA.z * 0.9,
      y: rRnd() * 3,
      v: 3 + rRnd(),
    }));
    const placeDrops = () => {
      for (let i = 0; i < rain.count; i++) rain.setMatrixAt(i, tmpM.makeTranslation(drops[i].x, drops[i].y, drops[i].z));
      rain.instanceMatrix.needsUpdate = true;
    };

    let dirty = true;
    const update = () => {
      const { plots: pl, weekIndex: w, month: m } = latest.current;
      const look = weekLook(pl[0].scenario.rain_mm, w, m, isDark, quality.maxRainDrops);
      (scene.background as THREE.Color).setHex(look.sky);
      grassMat.color.setHex(look.grass);
      pl.forEach((p, i) => plotApis[i].update(plotWeek(p.option, p.scenario, w)));
      rain.count = look.rainDrops;
      placeDrops();
      renderer.shadowMap.needsUpdate = true;
      dirty = true;
    };
    apiRef.current = { update };
    update();

    // --- Render loop: fps sampling (2D fallback), motion only when allowed, paused off screen ---
    let onScreen = true;
    const io = typeof IntersectionObserver !== "undefined" ? new IntersectionObserver((e) => {
      onScreen = e.some((x) => x.isIntersecting);
      if (onScreen) dirty = true;
    }) : null;
    io?.observe(container);
    let raf = 0;
    let last = 0;
    let firstFrame = 0;
    let sampleStart = 0;
    let sampled = false;
    let prev = 0;
    let t = 0;
    const deltas: number[] = [];
    const animate = (now: number) => {
      raf = requestAnimationFrame(animate);
      if (!onScreen) {
        last = prev = 0;
        return;
      }
      if (!sampled) {
        if (!firstFrame) firstFrame = now;
        if (last > 0 && now - firstFrame >= 500) {
          if (!sampleStart) sampleStart = now;
          deltas.push(now - last);
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
        const dt = prev ? Math.min(0.1, (now - prev) / 1000) : 0;
        prev = now;
        t += dt;
        if (rain.count > 0) {
          for (let i = 0; i < rain.count; i++) {
            drops[i].y -= drops[i].v * dt;
            if (drops[i].y < 0) drops[i].y += 3;
          }
          placeDrops();
          dirty = true;
        }
        for (const s of sprays) {
          if (!s.on) continue;
          s.group.rotation.y = t * 1.6;
          dirty = true;
        }
      }
      if (dirty || !sampled) {
        renderer.render(scene, camera);
        dirty = false;
      }
    };
    raf = requestAnimationFrame(animate);

    const onResize = () => {
      if (canvas.clientWidth === 0 || canvas.clientHeight === 0) return;
      fit();
      renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
      dirty = true;
    };
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(onResize) : null;
    ro?.observe(canvas);
    window.addEventListener("resize", onResize);

    return () => {
      apiRef.current = null;
      cancelAnimationFrame(raf);
      io?.disconnect();
      ro?.disconnect();
      window.removeEventListener("resize", onResize);
      scene.traverse((o) => {
        if (o instanceof THREE.InstancedMesh) o.dispose();
      });
      for (const d of disposables) d.dispose();
      sun.shadow.map?.dispose();
      renderer.dispose();
    };
  }, [isDark, quality, reducedMotion]);

  useEffect(() => {
    apiRef.current?.update();
  }, [plots, weekIndex, month]);

  return (
    <div ref={containerRef} className="farm-canvas-wrap">
      <canvas ref={canvasRef} className="farm-canvas" aria-hidden="true" />
    </div>
  );
}

/** Crop keys the farm draws (for tests and the legend). */
export const FARM_CROPS = CROPS;
