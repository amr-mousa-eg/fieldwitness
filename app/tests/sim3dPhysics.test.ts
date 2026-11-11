// Parity of the in-browser 3D replay (src/field3d/physics.ts) with the Python 3D path
// (fieldwitness.packs.sim3d.simulate_weekly). Tolerances were fixed before the first run
// (DECISIONS.md 2026-11-11, Rotation Builder Level B):
//   soil water, rain, irrigation <= 0.05 mm per week; Ks and canopy proxy <= 0.005;
//   crops and stages exact; root depth exact (both round to 0.01 m).
// 1) all 200 public packs: every precomputed alternative (and Current when it has no
//    history-only season) vs the shipped 3D series. The packs round to 0.1 mm / 0.01, so the
//    pack's own rounding (<= half a unit) is allowed on top (CI-safe, uses public files).
// 2) local reference (results/validation/sim3d_parity_ref, gitignored, written by
//    `python -m fieldwitness.packs.sim3d_inputs ks_t14slh --reference 20`): 20 fields spread over
//    the spatial blocks x all 36 ranked rotations x 3 weather cases, unrounded, same tolerances.
//    The summary is written to results/validation/sim3d_parity.json.
import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { simulateOption } from "../src/field3d/physics";
import { isHistoryOnly } from "../src/seasons";
import { type WeatherCase } from "../src/field3d/physics";
import type { FieldSim3D, FieldSim3DInputs, Sim3DOption } from "../src/types";

const PACKS = join(import.meta.dirname, "../public/packs/ks_t14slh");
const REF = join(import.meta.dirname, "../../results/validation/sim3d_parity_ref");
const OUT = join(import.meta.dirname, "../../results/validation/sim3d_parity.json");
const hasPacks = existsSync(PACKS) && readdirSync(PACKS).some((f) => f.endsWith(".sim3d_inputs.json"));
const hasRef = existsSync(REF) && hasPacks;

const TOL = { soil_water_mm: 0.05, rain_mm: 0.05, irrigation_mm: 0.05, ks: 0.005, canopy_cover: 0.005 } as const;
const SERIES = Object.keys(TOL) as (keyof typeof TOL)[];
const CASES: WeatherCase[] = ["normal", "dry", "hot"];
const load = <T>(p: string): T => JSON.parse(readFileSync(p, "utf8")) as T;
const maxDiff = (a: number[], b: number[]) => a.reduce((m, x, i) => Math.max(m, Math.abs(x - b[i])), 0);

function compare(ts: Sim3DOption, ref: Sim3DOption, slack: Partial<Record<keyof typeof TOL, number>>, worst: Record<string, number>) {
  expect(ts.crops).toEqual(ref.crops);
  expect(ts.stages).toEqual(ref.stages);
  expect(ts.root_depth_m).toEqual(ref.root_depth_m);
  for (const sid of Object.keys(ts.scenarios)) {
    for (const k of SERIES) {
      const d = maxDiff(ts.scenarios[sid][k], ref.scenarios[sid][k]);
      worst[k] = Math.max(worst[k] ?? 0, d);
      expect(d, `${ref.option_id} ${sid} ${k}`).toBeLessThanOrEqual(TOL[k] + (slack[k] ?? 0) + 1e-9);
    }
  }
}

describe.skipIf(!hasPacks)("3D replay vs the shipped 3D packs (all 200 fields)", () => {
  it("matches every precomputed option within tolerance + pack rounding", () => {
    const files = readdirSync(PACKS).filter((f) => f.endsWith(".sim3d_inputs.json"));
    expect(files).toHaveLength(200);
    const worst: Record<string, number> = {};
    let n = 0;
    for (const f of files) {
      const inp = load<FieldSim3DInputs>(join(PACKS, f));
      const pack = load<FieldSim3D>(join(PACKS, `${inp.field_id}.sim3d.json`));
      expect(inp.weather_year).toBe(pack.weather_year);
      for (const opt of [pack.current, ...pack.alternatives]) {
        if (opt.sequence.some(isHistoryOnly)) continue; // drawn with a placeholder, not simulated
        const ts = simulateOption(inp, opt.sequence);
        const ref: Sim3DOption = {
          ...opt,
          scenarios: Object.fromEntries(Object.keys(ts.scenarios).map((sid) => [sid, opt.scenarios[sid]])),
        };
        // the pack rounds soil water/rain/irrigation to 0.1 and Ks/canopy to 0.01
        compare(ts, ref, { soil_water_mm: 0.05, rain_mm: 0.05, irrigation_mm: 0.05, ks: 0.005, canopy_cover: 0.005 }, worst);
        n++;
      }
    }
    expect(n).toBeGreaterThan(780);
  }, 120_000);
});

interface RefFile {
  field_id: string;
  options: {
    sequence: string[];
    crops: string[];
    stages: string[];
    root_depth_m: number[];
    canopy_cover: number[];
    cases: Record<WeatherCase, Record<"soil_water_mm" | "ks" | "irrigation_mm" | "rain_mm", number[]>>;
  }[];
}

describe.skipIf(!hasRef)("3D replay vs unrounded Python reference (20 fields x 36 rotations x 3 weathers)", () => {
  it("matches within the stated tolerance; writes results/validation/sim3d_parity.json", () => {
    const files = readdirSync(REF).filter((f) => f.endsWith(".json"));
    expect(files.length).toBeGreaterThanOrEqual(20);
    const worst: Record<string, number> = {};
    let options = 0;
    for (const f of files) {
      const ref = load<RefFile>(join(REF, f));
      const inp = load<FieldSim3DInputs>(join(PACKS, `${ref.field_id}.sim3d_inputs.json`));
      for (const o of ref.options) {
        const ts = simulateOption(inp, o.sequence, CASES);
        const asOpt: Sim3DOption = {
          option_id: o.sequence.join("|"),
          sequence: o.sequence,
          rank: -1,
          label: "",
          crops: o.crops,
          stages: o.stages,
          root_depth_m: o.root_depth_m,
          scenarios: Object.fromEntries(
            CASES.map((c) => [
              inp.weather.cases[c],
              { ...o.cases[c], canopy_cover: o.canopy_cover, taw_mm: Array(156).fill(inp.params.taw_mm) },
            ]),
          ),
        };
        compare(ts, asOpt, {}, worst);
        options++;
      }
    }
    writeFileSync(
      OUT,
      JSON.stringify(
        {
          what: "Parity of app/src/field3d/physics.ts with fieldwitness.packs.sim3d.simulate_weekly",
          fields: files.length,
          rotations_per_field: options / files.length,
          weather_cases: CASES,
          option_runs: options * CASES.length,
          tolerance: { ...TOL, crops_stages_roots: "exact" },
          max_abs_difference: worst,
          passed: true,
          tag: "D",
        },
        null,
        2,
      ) + "\n",
    );
  }, 120_000);
});
