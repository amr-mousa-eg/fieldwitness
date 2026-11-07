import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { WITNESSES, backtestMetrics, backtestOffsets, backtestRows, inside, ledgerModes, missingWitnesses, witnessRows } from "../src/advisor";
import type { FieldPack, Tagged } from "../src/types";

const DIR = join(import.meta.dirname, "../fixtures/ks_demo_synthetic");
const packs = readdirSync(DIR)
  .filter((f) => /^[0-9a-f]{40}\.SYNTHETIC\.json$/.test(f))
  .map((f) => JSON.parse(readFileSync(join(DIR, f), "utf8")) as FieldPack);

const v = (value: number | null, lo90?: number, hi90?: number): Tagged => ({
  value,
  lo90,
  hi90,
  unit: "mm",
  tag: "D",
  source: "test",
});

describe("witnessRows", () => {
  it("puts every witness result of an option in exactly one cell", () => {
    for (const p of packs) {
      for (const o of p.options) {
        const rows = witnessRows(o);
        const cells = rows.flatMap((r) => WITNESSES.map((w) => r.cells[w]).filter(Boolean));
        expect(cells).toHaveLength(o.witnesses.length);
        for (const r of rows) for (const w of WITNESSES) expect(r.cells[w]?.witness ?? w).toBe(w);
      }
    }
  });

  it("names witnesses with no estimate (fixtures have no neighbour witness yet)", () => {
    expect(missingWitnesses(packs[0].options[0])).toEqual(["neighbours"]);
  });
});

describe("inside", () => {
  it("checks the closed interval and returns null without a range or observation", () => {
    expect(inside(v(10, 5, 15), v(15), 90)).toBe(true);
    expect(inside(v(10, 5, 15), v(15.1), 90)).toBe(false);
    expect(inside(v(10), v(10), 90)).toBeNull();
    expect(inside(v(10, 5, 15), v(null), 90)).toBeNull();
    expect(inside(v(10, 5, 15), v(10), 50)).toBeNull();
  });
});

describe("backtestOffsets", () => {
  it("centres each season on its prediction", () => {
    const row = { season_year: 2023, season_index: 0, crop: "sorghum", mode: "forecast" as const };
    expect(
      backtestOffsets([
        { ...row, predicted: v(10, 4, 18), observed: v(13) },
        { ...row, predicted: v(10), observed: v(null) },
        { ...row, predicted: v(null), observed: v(5) },
      ]),
    ).toEqual([
      { pred: 0, err: [6, 8], obs: 3 },
      { pred: 0, err: undefined, obs: null },
      { pred: null, err: undefined, obs: null },
    ]);
  });
});

describe("backtestRows", () => {
  it("keeps only seasons with prediction and observation, oldest first", () => {
    for (const p of packs) {
      for (const m of backtestMetrics(p.ledger)) {
        const rows = backtestRows(p.ledger, m, "forecast");
        expect(rows.length).toBeGreaterThan(0);
        const years = rows.map((r) => r.season_year);
        expect(years).toEqual([...years].sort((a, b) => a - b));
        for (const r of rows) {
          expect(r.predicted.tag).toBe("D");
          expect(r.observed.tag).toBe("O");
        }
      }
    }
    expect(backtestRows(packs[0].ledger, "no_such_metric", "forecast")).toEqual([]);
  });
});

describe("backtestRows with two modes", () => {
  it("never mixes forecast and forced entries of the same season", () => {
    const ledger = packs[0].ledger.filter((e) => e.mode === "forecast");
    const both = [...ledger, ...ledger.map((e) => ({ ...e, mode: "forced" as const }))];
    expect(ledgerModes(both)).toEqual(["forecast", "forced"]);
    for (const m of backtestMetrics(both)) {
      expect(backtestRows(both, m, "forecast")).toEqual(backtestRows(ledger, m, "forecast"));
      expect(backtestRows(both, m, "forced").length).toBe(backtestRows(ledger, m, "forecast").length);
    }
  });
});

describe("optionName", () => {
  it("names fixture ids, pipeline sequence ids and Current", async () => {
    const { optionName } = await import("../src/strings");
    expect(optionName({ option_id: "current" })).toBe("Current");
    expect(optionName({ option_id: "sorghum|fallow|winter_wheat" })).toMatch(/^Sorghum → Fallow → /);
  });
});
