import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { MONTHS, monthValue, shadeLevel, vulnerabilityFor } from "../src/calendar";
import { formatNumber } from "../src/format";
import type { FieldCalendar, FieldPack } from "../src/types";

const DIR = join(import.meta.dirname, "../fixtures/ks_demo_synthetic");
const read = <T>(f: string): T => JSON.parse(readFileSync(join(DIR, f), "utf8"));
const packs = readdirSync(DIR)
  .filter((f) => /^[0-9a-f]{40}\.SYNTHETIC\.json$/.test(f))
  .map((f) => read<FieldPack>(f));

describe("formatNumber", () => {
  it("keeps small values visible and shares as percent", () => {
    expect(formatNumber(0.002, "m³/m³ anomaly per year")).toBe("0.002");
    expect(formatNumber(-0.258, "cm per year")).toBe("-0.26");
    expect(formatNumber(0.72, "score 0–1")).toBe("0.72");
    expect(formatNumber(0, "days")).toBe("0");
    expect(formatNumber(407.4, "mm/season")).toBe("407");
    expect(formatNumber(0.19, "probability")).toBe("19 %");
  });
});

describe("calendar helpers", () => {
  it("shades shares in 5 steps and keeps null as no data", () => {
    expect([0, 0.01, 0.25, 0.26, 0.5, 0.99, 1].map(shadeLevel)).toEqual([0, 1, 1, 2, 2, 4, 4]);
    expect(shadeLevel(null)).toBeNull();
  });

  it("reads month series by month number, not position", () => {
    expect(monthValue([3, 1, 2], [0.3, 0.1, 0.2], 1)).toBe(0.1);
    expect(monthValue([1, 2], [0.1, null], 2)).toBeNull();
    expect(monthValue([1, 2], [0.1, 0.2], 7)).toBeNull();
  });

  it("finds a calendar for every option and splits crops with and without vulnerability data", () => {
    for (const p of packs) {
      const cal = read<FieldCalendar>(`${p.field.field_id}.calendar.SYNTHETIC.json`);
      expect(cal.bare_observed.map((b) => b.month)).toEqual(MONTHS);
      for (const o of p.options) {
        expect(cal.bare_by_option[o.option_id]).toBeDefined();
        const { found, missing } = vulnerabilityFor(cal, o);
        expect(found.length + missing.length).toBe(new Set(o.sequence).size);
        for (const v of found) expect(o.sequence).toContain(v.crop);
      }
    }
  });
});
