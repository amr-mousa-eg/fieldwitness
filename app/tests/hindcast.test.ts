import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { METHODS, badness, bestMethods, metricsOf, modesOf, rowsFor } from "../src/hindcast";
import type { HindcastRow, RegionHindcast } from "../src/types";

const h = JSON.parse(
  readFileSync(join(import.meta.dirname, "../fixtures/ks_demo_synthetic/hindcast.SYNTHETIC.json"), "utf8"),
) as RegionHindcast;

const row = (method: HindcastRow["method"], scores: Record<string, number>): HindcastRow => ({
  method,
  mode: "forecast",
  metric: "sos",
  n: 10,
  scores,
});

describe("hindcast helpers", () => {
  it("lists every method once per mode and metric, FieldWitness first", () => {
    for (const mode of modesOf(h)) {
      for (const metric of metricsOf(h, mode)) {
        expect(rowsFor(h, mode, metric).map((r) => r.method)).toEqual(METHODS);
      }
    }
  });

  it("scores coverage by distance to its nominal level, other scores by size", () => {
    expect(badness("covered90", 0.86)).toBeCloseTo(0.04);
    expect(badness("covered50", 0.45)).toBeCloseTo(0.05);
    expect(badness("timing_err_days", -3)).toBe(3);
    expect(badness("crps", 4.5)).toBe(4.5);
  });

  it("keeps ties and ignores rows without the score", () => {
    const rows = [row("B0", { crps: 2 }), row("B1", { crps: 2 }), row("B2", { crps: 3 }), row("B3", {})];
    expect([...bestMethods(rows, "crps")].sort()).toEqual(["B0", "B1"]);
    expect(bestMethods(rows, "covered90").size).toBe(0);
    expect([...bestMethods([row("B0", { covered90: 0.99 }), row("B1", { covered90: 0.85 })], "covered90")]).toEqual(["B1"]);
  });
});
