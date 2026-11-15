import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { LayerPanel } from "../src/LayerPanel";
import { PrintDossier } from "../src/PrintDossier";
import {
  DELTA_METRICS,
  type RegionOptionDeltas,
  deltaDomain,
  deltaRampForMetric,
  deltaTaggedMap,
  deltaValuesMap,
  isDeltaMetric,
  isImprovedDelta,
} from "../src/optionDeltas";
import { QrCodeSvg, encodeQrMatrix, qrSvgPath } from "../src/qrCode";
import { DEFAULT_PRIORITIES, NO_CONSTRAINTS } from "../src/rank";
import {
  compareHref,
  encodeFieldStateQuery,
  fieldStateHref,
  parseCompareQuery,
  parseFieldStateQuery,
  parseHash,
} from "../src/route";
import { setLocale } from "../src/strings";
import ar from "../src/strings/ar.json";
import en from "../src/strings/en.json";
import type { FieldPack, FieldScenarios, RegionIndex, RegionLayers } from "../src/types";

const ROOT = resolve(import.meta.dirname, "..", "..");
const readJson = <T>(rel: string): T => JSON.parse(readFileSync(resolve(ROOT, rel), "utf8")) as T;

describe("Phase P3 (E4.1 & E4.2 — Map Comparison, Synchronized Trend Scrubber, Shareable URL & QR)", () => {
  it("keeps 100% EN/AR string key parity", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(ar).sort());
  });

  it("optionDeltas.ts computes 0-centred diverging domains and validates real KS/UA packs synced to public", () => {
    expect(DELTA_METRICS).toEqual([
      "delta_water_use_mm",
      "delta_bad_year_water_mm",
      "delta_bare_months",
      "delta_ryi",
      "delta_erosion_exposure",
    ]);
    expect(isDeltaMetric("delta_water_use_mm")).toBe(true);
    expect(isDeltaMetric("erosion_exposure")).toBe(false);
    expect(isImprovedDelta("delta_water_use_mm", -120)).toBe(true);
    expect(isImprovedDelta("delta_water_use_mm", 45)).toBe(false);
    expect(isImprovedDelta("delta_ryi", 0.05)).toBe(true);
    expect(deltaRampForMetric("delta_water_use_mm")[0]).toBe("#01665e");
    expect(deltaRampForMetric("delta_ryi")[4]).toBe("#01665e");

    const ksDelta = readJson<RegionOptionDeltas>("packs/demo/ks_t14slh/option_deltas.json");
    const ksPub = readJson<RegionOptionDeltas>("app/public/packs/ks_t14slh/option_deltas.json");
    expect(ksPub).toEqual(ksDelta);
    expect(ksDelta.n_fields).toBe(200);
    expect(ksDelta.summary.delta_water_use_mm.valid_count).toBe(71);
    expect(ksDelta.summary.delta_water_use_mm.improved_count).toBe(71);
    expect(ksDelta.summary.delta_erosion_exposure.valid_count).toBe(118);

    const ksDom = deltaDomain(ksDelta, "delta_water_use_mm");
    expect(ksDom[0]).toBe(-ksDom[1]);
    expect(ksDom[0]).toBeLessThan(0);
    expect(Object.keys(deltaValuesMap(ksDelta, "delta_water_use_mm"))).toHaveLength(200);
    expect(Object.keys(deltaTaggedMap(ksDelta, "delta_water_use_mm"))).toHaveLength(200);

    const uaDelta = readJson<RegionOptionDeltas>("packs/demo/ua_central_t36uvu/option_deltas.json");
    const uaPub = readJson<RegionOptionDeltas>("app/public/packs/ua_central_t36uvu/option_deltas.json");
    expect(uaPub).toEqual(uaDelta);
    expect(uaDelta.n_fields).toBe(120);
    expect(uaDelta.summary.delta_water_use_mm.valid_count).toBe(120);
    expect(uaDelta.summary.delta_ryi.improved_count).toBe(80);
  });

  it("encodes deterministic ISO 18004 QR matrices with finder cores and dark module", () => {
    const sampleUrl = "https://example.org/#/ks_t14slh/abc123/options?pw=3,1,2,0,1&dt=2&dp=-20";
    const m1 = encodeQrMatrix(sampleUrl);
    const m2 = encodeQrMatrix(sampleUrl);
    expect(m1).toEqual(m2);
    const n = m1.length;
    expect(n).toBeGreaterThanOrEqual(21);
    expect((n - 17) % 4).toBe(0);

    // 3 corner 7x7 finder cores (centre 3x3 blocks all dark)
    for (const [r0, c0] of [
      [0, 0],
      [0, n - 7],
      [n - 7, 0],
    ]) {
      for (let dr = 2; dr <= 4; dr++) {
        for (let dc = 2; dc <= 4; dc++) {
          expect(m1[r0 + dr][c0 + dc]).toBe(true);
        }
      }
    }
    // Dark module always at (n - 8, 8)
    expect(m1[n - 8][8]).toBe(true);

    // Alternating timing pattern along row 6
    for (let c = 8; c < n - 8; c++) {
      expect(m1[6][c]).toBe(c % 2 === 0);
    }

    const { viewBoxSize, d } = qrSvgPath(m1);
    expect(viewBoxSize).toBe(n + 4);
    expect(d.length).toBeGreaterThan(200);

    const svg = renderToStaticMarkup(createElement(QrCodeSvg, { value: sampleUrl, size: 76, label: "Scan link" }));
    expect(svg).toContain('class="qr-code-svg"');
    expect(svg).toContain('aria-label="Scan link"');
    expect(svg).toContain(`viewBox="0 0 ${viewBoxSize} ${viewBoxSize}"`);
  });

  it("round-trips shareable field priorities, constraints, and weather scenarios cleanly through route hashes", () => {
    expect(encodeFieldStateQuery(DEFAULT_PRIORITIES, NO_CONSTRAINTS, 0, 0)).toBe("");

    const customP = { water: 3, bare: 2, badYear: 1, erosion: 0, legume: 3, residue: 1 };
    const customC = {
      dontWant: ["maize"],
      cantGrow: ["soybean"],
      canSell: ["winter_wheat", "sorghum"],
      irrigation: "yes" as const,
      waterCapMm: 450,
    };
    const href = fieldStateHref("ks_t14slh", "deadbeef01", "options", customP, customC, 2, -20);
    expect(href).toContain("#/ks_t14slh/deadbeef01/options?");

    const parsedRoute = parseHash(href);
    expect(parsedRoute).toEqual({
      regionId: "ks_t14slh",
      page: "map",
      fieldId: "deadbeef01",
      tab: "options",
    });

    const parsedState = parseFieldStateQuery(href);
    expect(parsedState.hasState).toBe(true);
    expect(parsedState.priorities).toEqual(customP);
    expect(parsedState.constraints).toEqual(customC);
    expect(parsedState.dt).toBe(2);
    expect(parsedState.dp).toBe(-20);

    // Invalid inputs ignored safely
    const badState = parseFieldStateQuery("#/ks_t14slh/abc/options?pw=9,9&dt=99&dp=-99");
    expect(badState.hasState).toBe(false);

    // Compare URL still parses cleanly alongside query changes
    const cHref = compareHref("ua_central_t36uvu", "f1", "f2");
    expect(parseHash(cHref).page).toBe("compare");
    expect(parseCompareQuery(cHref)).toEqual({ a: "f1", b: "f2" });
  });

  it("renders LayerPanel with S7 deltas, trend playback controls, synchronized snapshot, scale contract, and GIBS switcher", () => {
    const layers = readJson<RegionLayers>("packs/demo/ua_central_t36uvu/layers.json");
    const deltas = readJson<RegionOptionDeltas>("packs/demo/ua_central_t36uvu/option_deltas.json");
    const activeLayer = layers.layers[0];
    const midYear = activeLayer.grid.years[Math.floor(activeLayer.grid.years.length / 2)];

    setLocale("en");
    const html = renderToStaticMarkup(
      createElement(LayerPanel, {
        layers,
        optionDeltas: deltas,
        hasBasemap: true,
        choice: {
          colourBy: "delta_water_use_mm",
          layerId: activeLayer.layer_id,
          year: midYear,
          backdrop: "viirs",
        },
        set: () => {},
      }),
    );
    expect(html).toContain("Rank-1 alternative impact vs Current (S7)");
    expect(html).toContain("Δ Water use (Rank-1 vs Current)");
    expect(html).toContain("scrubber-transport");
    expect(html).toContain("▶ Play trend");
    expect(html).toContain("sync-snapshot");
    expect(html).toContain(`All regional NASA signals in ${midYear}`);
    expect(html).toContain("scale-contract-card");
    expect(html).toContain("Pixel scale contract");
    expect(html).toContain("backdrop-fieldset");
    expect(html).toContain("VIIRS SNPP True Color");

    setLocale("ar");
    const htmlAr = renderToStaticMarkup(
      createElement(LayerPanel, {
        layers,
        optionDeltas: deltas,
        hasBasemap: true,
        choice: {
          colourBy: "delta_water_use_mm",
          layerId: activeLayer.layer_id,
          year: midYear,
          backdrop: "modis",
        },
        set: () => {},
      }),
    );
    expect(htmlAr).toContain("عقد الدقة المكانية للبكسل");
    expect(htmlAr).toContain("أثر البديل الأول مقارنةً بالحالي (S7)");
    setLocale("en");
  });

  it("renders PrintDossier with customized profile notice and live scannable QR code", () => {
    const idx = readJson<RegionIndex>("packs/demo/ua_central_t36uvu/index.json");
    const fid = idx.fields[0].field_id;
    const pack = readJson<FieldPack>(`packs/demo/ua_central_t36uvu/${fid}.json`);
    const scenarios = readJson<FieldScenarios>(`packs/demo/ua_central_t36uvu/${fid}.scenarios.json`);

    setLocale("en");
    const html = renderToStaticMarkup(
      createElement(PrintDossier, {
        pack,
        regionId: "ua_central_t36uvu",
        index: idx,
        priorities: { water: 3, bare: 2, badYear: 1, erosion: 0, legume: 3, residue: 1 },
        constraints: { ...NO_CONSTRAINTS, irrigation: "no", waterCapMm: 400 },
        dt: 2,
        dp: -20,
        scenarios,
        shareUrl: `https://example.org/#/ua_central_t36uvu/${fid}/options?pw=3,2,1,0,3,1&irr=no&cap=400&dt=2&dp=-20`,
      }),
    );
    expect(html).toContain("print-profile-banner");
    expect(html).toContain("Custom priority weights &amp; farm constraints applied");
    expect(html).toContain("Weather sensitivity test: +2 °C, −20 %");
    expect(html).toContain("print-qr-box");
    expect(html).toContain("qr-code-svg");
    expect(html).toContain("Scan to reopen this field with exact settings");
  });
});
