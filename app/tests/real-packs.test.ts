// Runs the app's data helpers over the REAL packs in public/packs (copied by
// scripts/sync-packs.mjs). Skipped when no packs were copied, so CI stays green without data.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { backtestMetrics, backtestRows, ledgerModes, witnessRows } from "../src/advisor";
import { modesOf, metricsOf } from "../src/hindcast";
import { COLOUR_METRICS, fieldValues, gridGeoJSON } from "../src/mapLayers";
import type { FieldPack, RegionHindcast, RegionIndex, RegionLayers, RegionList } from "../src/types";
import { currentFromPack } from "../src/CorrectionPanel";
import { applyCorrections, emptyCorrections } from "../src/corrections";
import { wktToGeometry } from "../src/wkt";

const DIR = join(import.meta.dirname, "../public/packs");
const read = <T>(p: string): T => JSON.parse(readFileSync(join(DIR, p), "utf8")) as T;
const has = existsSync(join(DIR, "regions.json"));

/** Every object with a `tag` key is a tagged value: rule 3 (O/D/E/A plus a source). */
function untagged(x: unknown, path: string, out: string[]): string[] {
  if (Array.isArray(x)) x.forEach((v, i) => untagged(v, `${path}[${i}]`, out));
  else if (x && typeof x === "object") {
    const o = x as Record<string, unknown>;
    if ("tag" in o && (!["O", "D", "E", "A"].includes(o.tag as string) || !o.source)) out.push(path);
    for (const [k, v] of Object.entries(o)) untagged(v, `${path}.${k}`, out);
  }
  return out;
}

describe.skipIf(!has)("real packs in public/packs", () => {
  const regions = has ? read<RegionList>("regions.json").regions : [];

  for (const { region_id: r } of regions) {
    it(`${r}: every field opens and the helpers accept it`, () => {
      const index = read<RegionIndex>(`${r}/index.json`);
      const ids = new Set(index.fields.map((f) => f.field_id));
      expect(ids.size).toBe(index.fields.length);
      const bad: string[] = [];
      for (const f of index.fields) {
        expect(() => wktToGeometry(f.geometry_wkt)).not.toThrow();
        const pack = read<FieldPack>(`${r}/${f.field_id}.json`);
        expect(pack.field.field_id).toBe(f.field_id);
        for (const o of pack.options) expect(() => witnessRows(o)).not.toThrow();
        for (const mode of ledgerModes(pack.ledger)) {
          for (const m of backtestMetrics(pack.ledger)) {
            const keys = backtestRows(pack.ledger, m, mode).map((x) => `${x.season_year}-${x.season_index}`);
            expect(new Set(keys).size).toBe(keys.length); // one row per season (React keys)
          }
        }
        for (const part of ["", ".series", ".calendar", ".scenarios"]) {
          const p = `${r}/${f.field_id}${part}.json`;
          untagged(read(p), p, bad);
        }
      }
      expect(bad.slice(0, 5)).toEqual([]);
    });

    it(`${r}: hindcast and layers match the index`, () => {
      const ids = new Set(read<RegionIndex>(`${r}/index.json`).fields.map((f) => f.field_id));
      const h = read<RegionHindcast>(`${r}/hindcast.json`);
      expect(modesOf(h).length).toBeGreaterThan(0);
      for (const m of modesOf(h)) expect(metricsOf(h, m).length).toBeGreaterThan(0);
      expect(ids.has(h.story_field_id)).toBe(true);
      const layers = read<RegionLayers>(`${r}/layers.json`);
      for (const m of COLOUR_METRICS) {
        for (const id of Object.keys(fieldValues(layers, m))) expect(ids.has(id)).toBe(true);
      }
      for (const l of layers.layers) for (const y of l.grid.years) expect(() => gridGeoJSON(l, y)).not.toThrow();
      expect(untagged(h, "hindcast", []).concat(untagged(layers, "layers", [])).slice(0, 5)).toEqual([]);
    });
  }
});

describe.skipIf(!has)("T6.9d farmer corrections on real packs", () => {
  const regions = has ? read<RegionList>("regions.json").regions : [];
  for (const { region_id: r } of regions) {
    it(`${r}: a corrected history changes the Current sequence and tags it E`, () => {
      const index = read<RegionIndex>(`${r}/index.json`);
      let tested = 0;
      for (const f of index.fields) {
        const pack = read<FieldPack>(`${r}/${f.field_id}.json`);
        const cur = currentFromPack(pack);
        if (!cur) continue;
        const allowed = new Set(pack.options.flatMap((o) => o.sequence));
        const year = cur.years[0];
        const other = [...allowed].find((c) => c !== cur.sequence[0]);
        if (!other) continue;
        const res = applyCorrections(cur, { ...emptyCorrections(), cropByYear: { [year]: other } }, allowed);
        expect(res.corrected.sequence[0]).toBe(other);
        expect(res.corrected.sequence).not.toEqual(cur.sequence);
        expect(res.sourceByYear[year]).toBe("farmer");
        expect(res.needsRerun).toBe(true);
        expect(res.notes.join(" ")).toContain("tag E");
        tested++;
      }
      expect(tested).toBeGreaterThan(0);
    });
  }
});
