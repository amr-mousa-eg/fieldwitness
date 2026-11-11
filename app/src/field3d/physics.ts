// In-browser replay of the Field in 3D simulation (Rotation Builder, Level B). Output tag D.
//
// A line-by-line port of `fieldwitness.packs.sim3d.simulate_weekly` (Python) for one sequence:
// - season layout: `physics.rotation._layout` (crop windows from sowing day + daily Kc curve,
//   cover crop in the gap before the next crop, other days fallow with Kc 0.3, p 0.55: tag A);
// - daily root-zone water balance: `physics.waterbal.run` with the fixed seasonal irrigation
//   budget policy: FAO-56 Eq. 82 (TAW, given), Eq. 83 (RAW = p TAW), Eq. 84 (Ks), Eq. 85 (Dr,
//   no capillary rise, no runoff); ETa cut so Dr never exceeds TAW; irrigation refills to field
//   capacity on days with Dr > RAW inside crop windows until the budget is used up;
// - weekly means/sums over days 365..1456 and the crop/stage/root labels of
//   `packs.sim3d._compute_option_metadata`.
// Every input comes from <field_id>.sim3d_inputs.json (no number is invented here). The port is
// only used if the parity test (tests/sim3dPhysics.test.ts) matches Python within the stated
// tolerance; anything it cannot place is reported, never estimated.

import type { FieldSim3DInputs, Sim3DInputSlot, Sim3DOption, Sim3DScenario } from "../types";

/** The three what-ifs the builder replays (T6.8 ids in `inputs.weather.cases`). */
export type WeatherCase = "normal" | "dry" | "hot";

export const DAYS = 365;
export const T_DAYS = 4 * DAYS;
export const N_WEEKS = 156;
const FIRST_DAY = DAYS; // day 0-364 is spin-up

interface Layout {
  kc: Float64Array;
  p: Float64Array;
  owner: Int32Array;
  crop: Uint8Array;
  canopy: Float64Array;
  starts: number[];
}

/** `physics.rotation._layout`. Throws (like Python) when a sequence cannot be placed. */
export function layout(slots: Sim3DInputSlot[], kcFallow: number, pFallow: number): Layout {
  const S = slots.length;
  const T = (S + 1) * DAYS;
  const kc = new Float64Array(T).fill(kcFallow);
  const p = new Float64Array(T).fill(pFallow);
  const owner = new Int32Array(T).fill(-1);
  const crop = new Uint8Array(T);
  const canopy = new Float64Array(T);
  const starts = Array<number>(S).fill(-1);
  const crops = slots.flatMap((s, i) => (s.kind === "crop" ? [i] : []));
  const sow = new Map<number, [number, number]>();
  for (const i of crops) {
    const a = DAYS * (i + 1) + (slots[i].sow_day as number);
    const b = a + slots[i].kc.length;
    if (a < 0 || b > T) throw new Error(`slot ${i}: crop window leaves the timeline`);
    sow.set(i, [a, b]);
  }
  let prev: number | null = null;
  for (const i of crops) {
    const cur = sow.get(i) as [number, number];
    if (prev !== null) {
      const pw = sow.get(prev) as [number, number];
      if (cur[0] <= pw[0]) throw new Error("crops overlap completely; sequence not placeable");
      if (cur[0] < pw[1]) sow.set(prev, [pw[0], cur[0]]); // earlier crop cut at the next sowing
    }
    prev = i;
  }
  const clip01 = (x: number) => Math.min(1, Math.max(0, x));
  let cursor = DAYS;
  slots.forEach((s, i) => {
    if (s.kind === "crop") {
      const [a, b] = sow.get(i) as [number, number];
      for (let d = a; d < b; d++) {
        kc[d] = s.kc[d - a];
        p[d] = s.p;
        owner[d] = i;
        crop[d] = 1;
        canopy[d] = clip01(s.kc[d - a] / s.kc_mid);
      }
      starts[i] = a;
      cursor = b;
    } else if (s.kind === "cover") {
      const nxt = crops.filter((j) => j > i).map((j) => (sow.get(j) as [number, number])[0]);
      const limit = nxt.length ? nxt[0] : T;
      const a = Math.max(cursor, DAYS);
      const n = Math.min(limit - a, s.kc.length);
      if (n > 0) {
        for (let d = a; d < a + n; d++) {
          kc[d] = s.kc[d - a];
          p[d] = s.p;
          owner[d] = i;
          canopy[d] = clip01(s.kc[d - a] / s.kc_mid);
        }
        starts[i] = a;
        cursor = a + n;
      }
    }
  });
  return { kc, p, owner, crop, canopy, starts };
}

/** Python `round(x, 2)` for the root depths written to the 3D pack. */
const round2 = (x: number) => Number(x.toFixed(2));

/** Weekly crop, stage and root depth labels (`packs.sim3d._compute_option_metadata`). */
function weeklyLabels(seq: string[], slots: Sim3DInputSlot[], lay: Layout, zrIni: number) {
  const crops: string[] = [];
  const stages: string[] = [];
  const roots: number[] = [];
  for (let w = 0; w < N_WEEKS; w++) {
    const d = Math.min(FIRST_DAY + w * 7 + 3, T_DAYS - 1);
    const i = lay.owner[d];
    if (i >= 0 && lay.crop[d] && i < seq.length) {
      const s = slots[i];
      crops.push(seq[i]);
      const ds = Math.max(0, d - lay.starts[i]);
      const zrMax = s.zr_max_m;
      const [li, ld, lm] = s.stages_days;
      let rd: number;
      if (ds < li) {
        stages.push("initial");
        rd = zrIni + (ds / Math.max(1, li)) * 0.1 * (zrMax - zrIni);
      } else if (ds < li + ld) {
        stages.push("development");
        rd = zrIni + 0.1 * (zrMax - zrIni) + ((ds - li) / Math.max(1, ld)) * 0.9 * (zrMax - zrIni);
      } else if (ds < li + ld + lm) {
        stages.push("mid");
        rd = zrMax;
      } else {
        stages.push("late");
        rd = zrMax;
      }
      roots.push(round2(rd));
    } else {
      crops.push("fallow");
      stages.push("fallow");
      roots.push(0);
    }
  }
  return { crops, stages, roots };
}

/** FAO-56 Eq. 84 (as `waterbal.ks`): 1 while Dr <= RAW, linear to 0 at Dr = TAW, clipped. */
function ks(dr: number, taw: number, raw: number): number {
  const denom = taw > raw ? taw - raw : 1;
  const k = dr > raw ? (taw - dr) / denom : 1;
  return Math.min(1, Math.max(0, k));
}

/** One weather case: daily water balance (`waterbal.run`, fixed seasonal budget) + weekly series. */
function runCase(lay: Layout, reset: Uint8Array, rainY: number[], etoY: number[], inp: FieldSim3DInputs): Sim3DScenario {
  const { taw_mm: taw, kc_scale: kcScale, budget_mm: budget } = inp.params;
  const dr = new Float64Array(T_DAYS);
  const kArr = new Float64Array(T_DAYS);
  const irrArr = new Float64Array(T_DAYS);
  let d0 = 0; // dr0 = 0, clipped to [0, TAW]
  let left = budget;
  for (let t = 0; t < T_DAYS; t++) {
    const raw = lay.p[t] * taw; // FAO-56 Eq. 83
    if (reset[t]) left = budget;
    const pe = rainY[t % DAYS] - 0 * rainY[t % DAYS]; // runoff fraction 0 (A)
    let need = d0 > raw ? d0 : 0;
    if (!lay.crop[t]) need = 0;
    const irr = Math.min(need, left);
    left = left - irr;
    const k = ks(d0, taw, raw);
    let eta = k * (lay.kc[t] * kcScale * etoY[t % DAYS]);
    let nw = d0 - pe - irr + eta; // FAO-56 Eq. 85, CR = 0
    nw = Math.max(nw, 0); // deep percolation takes water above field capacity
    const excess = nw > taw ? nw - taw : 0; // ETa cut so Dr <= TAW
    eta = eta - excess;
    nw = nw - excess;
    dr[t] = nw;
    kArr[t] = k;
    irrArr[t] = irr;
    d0 = nw;
  }
  const out: Sim3DScenario = {
    soil_water_mm: [],
    taw_mm: Array<number>(N_WEEKS).fill(taw),
    canopy_cover: [],
    ks: [],
    rain_mm: [],
    irrigation_mm: [],
  };
  for (let w = 0; w < N_WEEKS; w++) {
    let sw = 0;
    let kk = 0;
    let ir = 0;
    let rn = 0;
    let cn = 0;
    for (let j = 0; j < 7; j++) {
      const t = FIRST_DAY + w * 7 + j;
      sw += Math.max(0, taw - dr[t]);
      kk += kArr[t];
      ir += irrArr[t];
      rn += rainY[t % DAYS];
      cn += lay.canopy[t];
    }
    out.soil_water_mm.push(sw / 7);
    out.ks.push(kk / 7);
    out.irrigation_mm.push(ir);
    out.rain_mm.push(rn);
    out.canopy_cover.push(cn / 7);
  }
  return out;
}

/**
 * Weekly 3D series of `sequence` for the requested weather cases, keyed by the pack's what-if id
 * (e.g. "t+0_p+0") so the existing scene can play it. Throws for a key without slot inputs.
 */
export function simulateOption(
  inp: FieldSim3DInputs,
  sequence: string[],
  cases: WeatherCase[] = ["normal", "dry", "hot"],
  meta: { option_id: string; label: string; rank: number } = { option_id: sequence.join("|"), label: "", rank: -1 },
): Sim3DOption {
  const slots = sequence.map((k) => {
    const s = inp.slots.crops[k];
    if (!s) throw new Error(`no simulation inputs for ${k}`);
    return s;
  });
  const lay = layout(slots, inp.slots.kc_fallow, inp.slots.p_fallow);
  const reset = new Uint8Array(T_DAYS);
  for (const st of lay.starts) if (st >= 0 && st < T_DAYS) reset[st] = 1;
  const labels = weeklyLabels(sequence, slots, lay, inp.slots.zr_ini_m);
  const scenarios: Record<string, Sim3DScenario> = {};
  for (const c of cases) {
    const ser = inp.weather.series[c];
    scenarios[inp.weather.cases[c]] = runCase(lay, reset, ser.rain_mm, ser.eto_mm, inp);
  }
  return {
    ...meta,
    sequence,
    crops: labels.crops,
    stages: labels.stages,
    root_depth_m: labels.roots,
    scenarios,
  };
}
