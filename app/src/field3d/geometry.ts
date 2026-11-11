// Procedural geometry for the Field-in-3D illustration (no downloaded models).
// Every plant is built at unit height (y from 0 to 1) and scaled per instance from pack values.
import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import type { CropKind } from "./growth";
import { seededRandom } from "./growth";

/** Strip all attributes except position + normal so geometries can be merged. */
function clean(g: THREE.BufferGeometry): THREE.BufferGeometry {
  for (const name of Object.keys(g.attributes)) {
    if (name !== "position" && name !== "normal") g.deleteAttribute(name);
  }
  if (!g.index) g.setIndex([...Array(g.getAttribute("position").count).keys()]);
  if (!g.getAttribute("normal")) g.computeVertexNormals();
  return g;
}

function merge(parts: THREE.BufferGeometry[]): THREE.BufferGeometry {
  const merged = mergeGeometries(parts.map(clean), false);
  for (const p of parts) p.dispose();
  if (!merged) throw new Error("geometry merge failed");
  return merged;
}

/** Tapered stalk from y0 to y1. */
function stalk(r0: number, r1: number, y0: number, y1: number, radial = 5, tiltX = 0, tiltZ = 0): THREE.BufferGeometry {
  const g = new THREE.CylinderGeometry(r1, r0, y1 - y0, radial, 1, true);
  g.translate(0, (y1 - y0) / 2, 0);
  if (tiltX || tiltZ) {
    g.rotateX(tiltX);
    g.rotateZ(tiltZ);
  }
  g.translate(0, y0, 0);
  return g;
}

/**
 * Arching leaf ribbon: leaves the stalk at height y, rises, then droops; width tapers to a tip.
 * `yaw` is the leaf direction around the stalk.
 */
function leaf(y: number, yaw: number, length: number, width: number, rise: number, droop: number, segs = 6): THREE.BufferGeometry {
  const pos: number[] = [];
  const idx: number[] = [];
  const dir = new THREE.Vector3(Math.cos(yaw), 0, Math.sin(yaw));
  const side = new THREE.Vector3(-dir.z, 0, dir.x);
  for (let i = 0; i <= segs; i++) {
    const t = i / segs;
    const out = length * t;
    const up = rise * t - droop * t * t;
    const half = (width / 2) * Math.sin(Math.PI * Math.min(1, 0.15 + t * 0.85)) * (1 - 0.15 * t);
    const cx = dir.x * out;
    const cz = dir.z * out;
    const cy = y + up;
    pos.push(cx + side.x * half, cy, cz + side.z * half);
    pos.push(cx - side.x * half, cy, cz - side.z * half);
    if (i < segs) {
      const a = i * 2;
      idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

function blob(rx: number, ry: number, rz: number, y: number, ws = 6, hs = 5): THREE.BufferGeometry {
  const g = new THREE.SphereGeometry(1, ws, hs);
  g.scale(rx, ry, rz);
  g.translate(0, y, 0);
  return g;
}

/** Plant body (stalk + leaves) at unit height. Leaves alternate sides like grasses. */
export function plantBody(crop: Exclude<CropKind, "fallow">): THREE.BufferGeometry {
  if (crop === "winter_wheat") {
    // A clump of three thin tillers with narrow basal leaves.
    const parts: THREE.BufferGeometry[] = [];
    const tillers: [number, number][] = [
      [0, 0],
      [0.09, 0.06],
      [-0.07, -0.08],
    ];
    tillers.forEach(([tx, tz], i) => {
      const s = stalk(0.012, 0.008, 0, 0.92 - i * 0.05, 3, tz, -tx);
      parts.push(s);
      parts.push(leaf(0.18 + i * 0.05, i * 2.1, 0.32, 0.035, 0.22, 0.34, 3));
      parts.push(leaf(0.38 + i * 0.04, i * 2.1 + Math.PI, 0.26, 0.03, 0.18, 0.3, 3));
    });
    return merge(parts);
  }
  const isMaize = crop === "maize";
  const parts: THREE.BufferGeometry[] = [stalk(isMaize ? 0.028 : 0.024, 0.014, 0, 1, 5)];
  const nLeaves = isMaize ? 7 : 6;
  for (let i = 0; i < nLeaves; i++) {
    const t = i / (nLeaves - 1);
    const y = 0.12 + t * 0.7;
    const yaw = i * Math.PI + (i % 3) * 0.35; // alternate sides with a slight spiral
    const length = (isMaize ? 0.5 : 0.42) * (1 - 0.45 * t);
    const width = (isMaize ? 0.09 : 0.08) * (1 - 0.3 * t);
    parts.push(leaf(y, yaw, length, width, 0.22 * (1 - t * 0.5), 0.42, 4));
  }
  return merge(parts);
}

/** Head geometry at unit height: maize tassel + ear, wheat ears, sorghum panicle. */
export function plantHead(crop: Exclude<CropKind, "fallow">): THREE.BufferGeometry {
  if (crop === "winter_wheat") {
    const tips: [number, number, number][] = [
      [0, 0, 0.92],
      [0.09, 0.06, 0.87],
      [-0.07, -0.08, 0.82],
    ];
    return merge(
      tips.map(([x, z, y]) => {
        const g = blob(0.018, 0.075, 0.018, 0, 4, 3);
        g.translate(x * (y / 0.9), y + 0.06, z * (y / 0.9));
        return g;
      }),
    );
  }
  if (crop === "maize") {
    const tassel = [0, 1.3, 2.6, 3.9, 5.2].map((yaw) => {
      const g = stalk(0.006, 0.002, 0, 0.14, 3, 0.55);
      g.rotateY(yaw);
      g.translate(0, 0.96, 0);
      return g;
    });
    const spike = stalk(0.008, 0.003, 0.98, 1.14, 3);
    const ear = blob(0.035, 0.09, 0.035, 0, 5, 4);
    ear.rotateZ(0.35);
    ear.translate(0.05, 0.52, 0);
    return merge([...tassel, spike, ear]);
  }
  // sorghum: compact oval panicle on a short peduncle
  return merge([stalk(0.01, 0.008, 0.95, 1.02, 3), blob(0.06, 0.1, 0.06, 1.08, 6, 4)]);
}

/** Low weed rosette for fallow weeks. */
export function weedRosette(): THREE.BufferGeometry {
  const parts = [0, 1.25, 2.5, 3.75, 5].map((yaw) => leaf(0.005, yaw, 0.09, 0.035, 0.05, 0.06, 3));
  return merge(parts);
}

/**
 * Root system template at unit depth (y from 0 to −1) as line segments.
 * Maize and sorghum: a few thick-looking descending roots with laterals. Wheat: a fibrous mat.
 */
export function rootTemplate(crop: Exclude<CropKind, "fallow">, seed: number): THREE.BufferGeometry {
  const rnd = seededRandom(seed);
  const pts: number[] = [];
  const seg = (a: number[], b: number[]) => pts.push(...a, ...b);
  const strands = crop === "winter_wheat" ? 9 : 5;
  for (let s = 0; s < strands; s++) {
    const yaw = (s / strands) * Math.PI * 2 + rnd() * 0.5;
    const spread = crop === "winter_wheat" ? 0.08 + rnd() * 0.06 : 0.12 + rnd() * 0.1;
    let prev = [0, 0, 0];
    const steps = 5;
    for (let k = 1; k <= steps; k++) {
      const t = k / steps;
      const r = spread * Math.sqrt(t);
      const next = [Math.cos(yaw + t * 0.6) * r, -t * (0.75 + 0.25 * rnd()), Math.sin(yaw + t * 0.6) * r];
      seg(prev, next);
      if (k < steps && rnd() < 0.6) {
        const ly = yaw + (rnd() - 0.5) * 1.6;
        const ll = 0.05 + rnd() * 0.07;
        seg(next, [next[0] + Math.cos(ly) * ll, next[1] - 0.04 - rnd() * 0.06, next[2] + Math.sin(ly) * ll]);
      }
      prev = next;
    }
  }
  // Main root reaching the full rooting depth.
  seg([0, 0, 0], [0, -1, 0]);
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
  return g;
}

/** Fine soil grain texture: speckles on white, multiplied by each stratum colour. */
export function grainTexture(seed: number, size = 128): THREE.CanvasTexture | null {
  if (typeof document === "undefined") return null;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, size, size);
  const rnd = seededRandom(seed);
  for (let i = 0; i < size * size * 0.18; i++) {
    const v = 150 + Math.floor(rnd() * 90);
    ctx.fillStyle = `rgba(${v},${v},${v},${0.35 + rnd() * 0.4})`;
    const r = rnd() < 0.92 ? 1 : 2;
    ctx.fillRect(Math.floor(rnd() * size), Math.floor(rnd() * size), r, r);
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

/** A thin rectangular frame (4 slim boxes) used as the water fill line around the block. */
export function frameGeometry(width: number, thickness: number): THREE.BufferGeometry {
  const h = width / 2;
  const bars = [
    [0, h, width + thickness, thickness],
    [0, -h, width + thickness, thickness],
    [h, 0, thickness, width + thickness],
    [-h, 0, thickness, width + thickness],
  ].map(([x, z, sx, sz]) => {
    const g = new THREE.BoxGeometry(sx, thickness, sz);
    g.translate(x, 0, z);
    return g;
  });
  return merge(bars);
}
