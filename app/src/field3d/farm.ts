// Farm view: pure mapping from the weekly simulated series (pack or browser replay) to what the
// isometric farm draws. Nothing here invents a value: every visual state is a function of one
// week's pack values (crop, stage, canopy proxy, Ks, rain, irrigation, root depth) or of the
// calendar month. Colours, sizes and thresholds are display choices (tag A), never shown as
// numbers. Scenery (barn, trees, pond, fences, paths) is not data and is labelled so in the view.
import type { Sim3DOption, Sim3DScenario } from "../types";
import { headsVisible, historyOnlyKey, rainDropCount, seasonGrowth, showIrrigation, toCropKind } from "./growth";

export type PlotKind = "maize" | "sorghum" | "winter_wheat" | "cover" | "bare" | "not_simulated";

export interface PlotWeek {
  kind: PlotKind;
  /** History-only season key (e.g. perennial_forage) when kind is "not_simulated". */
  historyKey: string | null;
  /** 0–1 plant size: highest canopy proxy so far this season (crops) or this week's (cover). */
  growth: number;
  stage: string;
  heads: boolean;
  /** Late stage: crop turns straw-coloured. */
  ripe: boolean;
  /** 0 (no stress, Ks = 1) to 1 (Ks = 0): plants pale as in the glass view. */
  stress: number;
  /** Soil darkens with this week's soil water / TAW (0–1). */
  wetness: number;
  irrigating: boolean;
}

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));

/**
 * Cover-crop week: labelled "fallow" in the pack's crop list (no harvested crop) with a canopy
 * proxy > 0 from the cover crop's Kc curve, in a run of at least two such weeks. A single week
 * like that is a crop boundary (a week that straddles harvest or sowing): drawn as bare soil.
 * Checked on all 200 packs: rotations without a cover crop have no such run.
 */
export function isCoverWeek(option: Sim3DOption, scen: Sim3DScenario, w: number): boolean {
  const f = (i: number) => i >= 0 && i < option.crops.length && option.crops[i] === "fallow" && (scen.canopy_cover[i] ?? 0) > 0;
  return f(w) && (f(w - 1) || f(w + 1));
}

/** One plot in one week. */
export function plotWeek(option: Sim3DOption, scen: Sim3DScenario, week: number): PlotWeek {
  const w = Math.max(0, Math.min(week, scen.soil_water_mm.length - 1));
  const hist = historyOnlyKey(option.sequence, option.crops, w);
  const ks = scen.ks[w] ?? 1;
  const taw = scen.taw_mm[w] ?? 0;
  const base = {
    historyKey: null,
    stage: option.stages[w] ?? "fallow",
    heads: false,
    ripe: false,
    stress: clamp01(1 - ks),
    wetness: taw > 0 ? clamp01((scen.soil_water_mm[w] ?? 0) / taw) : 0,
    irrigating: showIrrigation(scen.irrigation_mm[w] ?? 0),
  };
  if (hist) {
    return { ...base, kind: "not_simulated", historyKey: hist, growth: 0, stress: 0, wetness: 0, irrigating: false };
  }
  const crop = toCropKind(option.crops[w]);
  if (crop === "fallow") {
    return isCoverWeek(option, scen, w)
      ? { ...base, kind: "cover", growth: clamp01(scen.canopy_cover[w] ?? 0) }
      : { ...base, kind: "bare", growth: 0 };
  }
  return {
    ...base,
    kind: crop,
    growth: seasonGrowth(option.crops, option.stages, scen.canopy_cover, w),
    heads: headsVisible(crop, base.stage),
    ripe: base.stage === "late",
  };
}

export interface WeekLook {
  /** Sky colour: grey-blue in rainy weeks, clear in dry ones, by season. */
  sky: number;
  /** Grass colour: green in the growing season, straw in winter, drier after dry weeks. */
  grass: number;
  /** 0–1 share of the last 4 weeks with less than DRY_WEEK_MM rain (same weather for both plots). */
  dryness: number;
  /** 0–1 rain intensity this week. */
  wet: number;
  rainDrops: number;
}

/** Week counted as dry for the look (display choice, A). */
export const DRY_WEEK_MM = 2;
/** Weekly rain that gives the fully overcast look (display choice, A). */
export const OVERCAST_MM = 25;

function lerpHex(a: number, b: number, t: number): number {
  const k = clamp01(t);
  const ch = (s: number) => [(s >> 16) & 255, (s >> 8) & 255, s & 255];
  const [ar, ag, ab] = ch(a);
  const [br, bg, bb] = ch(b);
  return (Math.round(ar + (br - ar) * k) << 16) | (Math.round(ag + (bg - ag) * k) << 8) | Math.round(ab + (bb - ab) * k);
}

const PALETTE = {
  light: { skySummer: 0x9fd3f2, skyWinter: 0xc9dbe6, skyRain: 0x8a98a6, grassSummer: 0x7fb55a, grassWinter: 0xb8ad78, grassDry: 0xc7b469 },
  dark: { skySummer: 0x1d3a55, skyWinter: 0x223040, skyRain: 0x262c33, grassSummer: 0x3f6b33, grassWinter: 0x5a5638, grassDry: 0x6a5f34 },
};

/** Growing-season weight of a month (1 in Jun–Aug, 0 in Dec–Feb): a smooth cosine, display only. */
export function summerness(month: number): number {
  return clamp01(0.5 - 0.5 * Math.cos(((month - 1.5) / 12) * 2 * Math.PI));
}

/** Sky and ground look of week `w` from the weekly rain (same weather for both plots) and month. */
export function weekLook(rainMm: number[], w: number, month: number, isDark: boolean, maxDrops: number): WeekLook {
  const p = isDark ? PALETTE.dark : PALETTE.light;
  const rain = rainMm[w] ?? 0;
  const recent = rainMm.slice(Math.max(0, w - 3), w + 1);
  const dryness = recent.length ? recent.filter((r) => r < DRY_WEEK_MM).length / recent.length : 0;
  const wet = clamp01(rain / OVERCAST_MM);
  const s = summerness(month);
  const sky = lerpHex(lerpHex(p.skyWinter, p.skySummer, s), p.skyRain, wet);
  const grass = lerpHex(lerpHex(p.grassWinter, p.grassSummer, s), p.grassDry, dryness * s * 0.8);
  return { sky, grass, dryness, wet, rainDrops: rainDropCount(rain, maxDrops) };
}

/** Telemetry for the metric strip under the farm (same fields as the glass view). */
export function weekTelemetry(option: Sim3DOption, scen: Sim3DScenario, week: number) {
  const w = Math.max(0, Math.min(week, scen.soil_water_mm.length - 1));
  return {
    week: w,
    crop: option.crops[w] ?? "fallow",
    stage: option.stages[w] ?? "fallow",
    soilWater: scen.soil_water_mm[w] ?? 0,
    taw: scen.taw_mm[w] ?? 0,
    canopyCover: scen.canopy_cover[w] ?? 0,
    ks: scen.ks[w] ?? 1,
    rain: scen.rain_mm[w] ?? 0,
    irrigation: scen.irrigation_mm[w] ?? 0,
    rootDepth: option.root_depth_m[w] ?? 0,
    historyOnly: historyOnlyKey(option.sequence, option.crops, w),
    cover: isCoverWeek(option, scen, w),
  };
}
