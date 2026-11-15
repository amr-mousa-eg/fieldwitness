import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { formatTagged, unitLabel } from "../src/format";
import { modesOf, metricsOf, rowsFor } from "../src/hindcast";
import { DIVERGING, gridDomain, gridGeoJSON } from "../src/mapLayers";
import { setLocale } from "../src/strings";
import type { RegionHindcast, RegionLayers } from "../src/types";

const PACKS_DIR = join(import.meta.dirname, "../public/packs");
const HAS_PACKS = existsSync(join(PACKS_DIR, "ua_central_t36uvu/layers.json"));
const read = <T>(rel: string): T => JSON.parse(readFileSync(join(PACKS_DIR, rel), "utf8")) as T;

describe("Phase P0 regional layer unit localisation", () => {
  it("translates regional GRACE, SMAP, and POWER heat-wave units in Arabic", () => {
    setLocale("en");
    expect(unitLabel("days/year")).toBe("days/year");
    setLocale("ar");
    expect(unitLabel("days/year")).toBe("يوم/سنة");
    expect(unitLabel("days/year per year")).toBe("يوم/سنة سنوياً");
    expect(unitLabel("cm water-equivalent anomaly (vs 2004-2009 mean)")).toContain("سم");
    expect(unitLabel("m3/m3 anomaly vs monthly climatology")).toContain("م³/م³");
    expect(
      formatTagged({ value: 14, unit: "days/year", tag: "D", source: "NASA POWER" }, 0),
    ).toContain("يوم/سنة");
    setLocale("en");
  });
});

describe.skipIf(!HAS_PACKS)("Phase P0 synced regional layers and Ukraine baselines", () => {
  it("populates ua_central_t36uvu/layers.json with GRACE TWS and POWER heatwave_days", () => {
    const layers = read<RegionLayers>("ua_central_t36uvu/layers.json");
    const ids = layers.layers.map((l) => l.layer_id);
    expect(ids).toContain("grace_tws");
    expect(ids).toContain("heatwave_days");
    for (const l of layers.layers) {
      expect(l.scale_flag).toBe(true);
      expect(l.grid.cells.length).toBeGreaterThan(0);
      expect(l.region_mean.x.length).toBeGreaterThanOrEqual(20);
      expect(l.trend.value).not.toBeNull();
      const [lo, hi] = gridDomain(l);
      expect(hi).toBeGreaterThan(lo);
      const fc = gridGeoJSON(l, l.grid.years[l.grid.years.length - 1]);
      expect(fc.features.length).toBe(l.grid.cells.length);
    }
    expect(DIVERGING.has("grace_tws")).toBe(true);
    expect(DIVERGING.has("heatwave_days")).toBe(false);
  });

  it("adds heatwave_days to ks_t14slh/layers.json alongside grace_tws and smap_anomaly", () => {
    const layers = read<RegionLayers>("ks_t14slh/layers.json");
    const ids = layers.layers.map((l) => l.layer_id);
    expect(ids).toEqual(["grace_tws", "smap_anomaly", "heatwave_days"]);
    const hw = layers.layers.find((l) => l.layer_id === "heatwave_days")!;
    expect(hw.scale_flag).toBe(true);
    expect(hw.grid.cells.length).toBe(9);
    expect(hw.grid.years[0]).toBe(2001);
  });

  it("ships leak-free B0, B1, B2 and fieldwitness multi-metric hindcast baselines for Ukraine", () => {
    const h = read<RegionHindcast>("ua_central_t36uvu/hindcast.json");
    expect(h.cutoff).toBe("2021-12-31");
    expect(h.crop_observed_source).toBe("classifier");
    expect(modesOf(h)).toEqual(["forecast", "forced"]);
    const metrics = metricsOf(h, "forecast");
    expect(metrics).toEqual(["sos", "peak", "canopy_integral", "cover_days"]);
    for (const m of metrics) {
      const rows = rowsFor(h, "forecast", m);
      expect(rows.map((r) => r.method)).toEqual(["fieldwitness", "B0", "B1", "B2"]);
      for (const r of rows) {
        expect(r.n).toBeGreaterThan(200);
        expect(typeof r.scores.crps).toBe("number");
        expect(typeof r.scores.covered50).toBe("number");
        expect(typeof r.scores.covered90).toBe("number");
        expect(typeof r.scores.mae_median).toBe("number");
      }
    }
  });
});
