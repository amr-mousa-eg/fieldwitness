// Pure mapping from simulated pack values to what the 3D illustration draws.
// Nothing here invents data: every visual quantity is a function of a value already in the
// .sim3d.json pack (canopy proxy, Ks, soil water, TAW, rain, irrigation, root depth, crop, stage).
// Visual sizes (plant heights in scene units, counts) are display choices, never shown as numbers.

export type CropKind = "maize" | "winter_wheat" | "sorghum" | "fallow";

export interface QualityTier {
  name: "high" | "low";
  /** Upper bound for renderer pixel ratio. */
  dprCap: number;
  antialias: boolean;
  /** Hard cap on plant instances per scene (all crop parts together). */
  maxPlantInstances: number;
  maxRainDrops: number;
  weeds: number;
  shadowMapSize: number;
  /** Segments per side of the animated water surface. */
  waterSegments: number;
  /** Root systems drawn per side (n × n). */
  rootGrid: number;
}

export const HIGH_TIER: QualityTier = {
  name: "high",
  dprCap: 2,
  antialias: true,
  maxPlantInstances: 1600,
  maxRainDrops: 240,
  weeds: 24,
  shadowMapSize: 1024,
  waterSegments: 24,
  rootGrid: 4,
};

export const LOW_TIER: QualityTier = {
  name: "low",
  dprCap: 1.25,
  antialias: false,
  maxPlantInstances: 420,
  maxRainDrops: 80,
  weeds: 10,
  shadowMapSize: 512,
  waterSegments: 12,
  rootGrid: 3,
};

/** Phones (< 640 px wide) and low-core devices get the low tier. */
export function pickQuality(viewportWidth: number, hardwareConcurrency: number | undefined): QualityTier {
  const cores = hardwareConcurrency ?? 8;
  return viewportWidth < 640 || cores <= 4 ? LOW_TIER : HIGH_TIER;
}

/** Plants per side for a crop; parts per plant (stalk + head) count against the tier cap. */
export function plantsPerSide(crop: CropKind, tier: QualityTier): number {
  if (crop === "fallow") return 0;
  const wanted = tier.name === "high" ? { maize: 11, sorghum: 12, winter_wheat: 20 }[crop] : { maize: 6, sorghum: 6, winter_wheat: 9 }[crop];
  const partsPerPlant = 2; // body + head instance
  const capPerSide = Math.floor(Math.sqrt(tier.maxPlantInstances / partsPerPlant));
  return Math.min(wanted, capPerSide);
}

export function toCropKind(crop: string | undefined): CropKind {
  return crop === "maize" || crop === "winter_wheat" || crop === "sorghum" ? crop : "fallow";
}

/**
 * Growth fraction (0–1) used for plant height: the highest canopy proxy reached so far in the
 * current crop season. Height does not shrink when the canopy proxy declines in the late stage.
 * A season ends at a crop change or when a "late" stage is followed by a new stage.
 */
export function seasonGrowth(crops: string[], stages: string[], canopy: number[], w: number): number {
  const crop = crops[w];
  if (!crop || crop === "fallow") return 0;
  let start = w;
  while (start > 0 && crops[start - 1] === crop && !(stages[start - 1] === "late" && stages[start] !== "late")) {
    start--;
  }
  let g = 0;
  for (let i = start; i <= w; i++) g = Math.max(g, canopy[i] ?? 0);
  return clamp01(g);
}

/** Heads (tassel/ear, wheat ear, sorghum panicle) show from the mid stage onward. */
export function headsVisible(crop: CropKind, stage: string): boolean {
  return crop !== "fallow" && (stage === "mid" || stage === "late");
}

/** Soil water as a fraction of total available water; drives the fill line. */
export function waterFillFraction(soilWaterMm: number, tawMm: number): number {
  if (!(tawMm > 0)) return 0;
  return clamp01(soilWaterMm / tawMm);
}

/** Rain drops drawn this week: proportional to weekly rain, 0 when the week had no rain. */
export function rainDropCount(rainMm: number, cap: number): number {
  if (!(rainMm > 0)) return 0;
  return Math.max(1, Math.min(cap, Math.round((cap * rainMm) / 40)));
}

/** Irrigation lines are shown only for weeks where the model applied irrigation. */
export function showIrrigation(irrigationMm: number): boolean {
  return irrigationMm > 0;
}

/** Visual height of a mature plant in scene units (soil block is 1.6 deep). Not to scale. */
export const MATURE_HEIGHT: Record<Exclude<CropKind, "fallow">, number> = {
  maize: 1.15,
  sorghum: 0.95,
  winter_wheat: 0.6,
};

export function median(xs: number[]): number {
  if (xs.length === 0) return NaN;
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/** p-th percentile (0–100) by nearest rank. */
export function percentile(xs: number[], p: number): number {
  if (xs.length === 0) return NaN;
  const s = [...xs].sort((a, b) => a - b);
  const idx = Math.min(s.length - 1, Math.max(0, Math.ceil((p / 100) * s.length) - 1));
  return s[idx];
}

/** Frames-per-second from rAF deltas (ms). */
export function fpsStats(deltasMs: number[]): { median: number; p10: number } {
  const fps = deltasMs.filter((d) => d > 0).map((d) => 1000 / d);
  return { median: median(fps), p10: percentile(fps, 10) };
}

/**
 * Fallback cut-off: 30 fps minus a small tolerance. Browsers draw on vsync steps, so a device that
 * steadily renders every other 60 Hz frame measures 29.9–30.0; that is 30 fps, not a poor frame rate.
 */
export const MIN_MEDIAN_FPS = 28;
export const FPS_SAMPLE_MS = 2000;
export const FPS_MIN_FRAMES = 20;

export function isTooSlow(deltasMs: number[]): boolean {
  const { median: m } = fpsStats(deltasMs);
  return Number.isFinite(m) && m < MIN_MEDIAN_FPS;
}

/** Deterministic PRNG (mulberry32) so the field layout is the same on every load. */
export function seededRandom(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const SEED = 20261114;

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}
