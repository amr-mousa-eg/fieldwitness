// History-only seasons (perennial forage, non-arable, ...) are never shown as simulated values:
// Field in 3D shows "<crop> (history only; not simulated)" with a neutral placeholder (no crop,
// no bare-fallow weeds), the Calendar lists them apart, the Field Card gives them no constraint row.
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { vulnerabilityFor } from "../src/calendar";
import { historyOnlyKey } from "../src/field3d/growth";
import { isHistoryOnly } from "../src/seasons";
import { cropName, t } from "../src/strings";
import type { FieldCalendar, FieldSim3D } from "../src/types";

const DIR = join(import.meta.dirname, "../public/packs/ks_t14slh");
const hasPacks = existsSync(DIR);
const PERENNIAL_FIELD = "189e236596fa05b85f1c19fe582083601b59b353"; // current: perennial forage → sorghum → sorghum

describe("history-only seasons", () => {
  it("only the modelled season keys are simulated", () => {
    for (const k of ["maize", "sorghum", "winter_wheat", "fallow", "cover_crop"]) expect(isHistoryOnly(k)).toBe(false);
    for (const k of ["perennial_forage", "non_arable", "other_annual", "soybean"]) expect(isHistoryOnly(k)).toBe(true);
  });

  it("label reads 'Perennial forage (history only; not simulated)'", () => {
    expect(t("season.historyOnly", { crop: cropName("perennial_forage") })).toBe(
      "Perennial forage (history only; not simulated)",
    );
  });

  it("week owner: history weeks of the season's year, but a drawn crop (autumn winter wheat) stays", () => {
    const seq = ["perennial_forage", "winter_wheat", "sorghum"];
    const crops = Array<string>(156).fill("fallow");
    for (let w = 41; w < 52 + 30; w++) crops[w] = "winter_wheat";
    expect(historyOnlyKey(seq, crops, 0)).toBe("perennial_forage");
    expect(historyOnlyKey(seq, crops, 40)).toBe("perennial_forage");
    expect(historyOnlyKey(seq, crops, 41)).toBeNull();
    expect(historyOnlyKey(seq, crops, 60)).toBeNull();
    expect(historyOnlyKey(seq, crops, 155)).toBeNull();
    expect(historyOnlyKey(["fallow", "maize", "fallow"], crops, 0)).toBeNull();
  });

  it("calendar lists history-only states apart, not as a missing vulnerability calendar", () => {
    const cal = { vulnerability: [{ crop: "sorghum" }] } as unknown as FieldCalendar;
    const r = vulnerabilityFor(cal, { sequence: ["perennial_forage", "sorghum", "sorghum"] });
    expect(r.historyOnly).toEqual(["perennial_forage"]);
    expect(r.missing).toEqual([]);
    expect(r.found).toHaveLength(1);
  });
});

describe.skipIf(!hasPacks)("history-only seasons in the real packs", () => {
  const files = hasPacks ? readdirSync(DIR).filter((f) => f.endsWith(".sim3d.json")) : [];
  const load = (f: string): FieldSim3D => JSON.parse(readFileSync(join(DIR, f), "utf8"));

  it("the perennial-forage field: every week of season 1 is history only, none of seasons 2-3", () => {
    const opt = load(`${PERENNIAL_FIELD}.sim3d.json`).current;
    expect(opt.sequence[0]).toBe("perennial_forage");
    for (let w = 0; w < 52; w++) expect(historyOnlyKey(opt.sequence, opt.crops, w)).toBe("perennial_forage");
    for (let w = 52; w < 156; w++) expect(historyOnlyKey(opt.sequence, opt.crops, w)).toBeNull();
  });

  it("all packs: a history-only season never reaches a drawn crop or a simulated week", () => {
    let hist = 0;
    for (const f of files) {
      const s = load(f);
      for (const opt of [s.current, ...s.alternatives]) {
        for (let w = 0; w < opt.crops.length; w++) {
          const key = opt.sequence[Math.min(opt.sequence.length - 1, Math.floor(w / 52))];
          const h = historyOnlyKey(opt.sequence, opt.crops, w);
          if (h) {
            hist++;
            expect(isHistoryOnly(key)).toBe(true);
            expect(opt.crops[w]).toBe("fallow"); // the pack's placeholder, now never shown as bare fallow
          } else if (isHistoryOnly(key)) {
            expect(opt.crops[w]).not.toBe("fallow");
          }
        }
        // ranked alternatives are candidates, so they never hold a history state
        if (opt !== s.current) expect(opt.sequence.some(isHistoryOnly)).toBe(false);
      }
    }
    expect(hist).toBeGreaterThan(0);
  });
});
