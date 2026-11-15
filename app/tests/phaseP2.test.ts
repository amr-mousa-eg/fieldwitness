import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ObservedChecks } from "../src/CalendarView";
import { OBS_CHECK_KEYS } from "../src/calendar";
import { setLocale } from "../src/strings";
import ar from "../src/strings/ar.json";
import en from "../src/strings/en.json";
import type { FieldCalendar, RegionIndex } from "../src/types";

const ROOT = resolve(import.meta.dirname, "..", "..");
const readPackJson = <T>(rel: string): T => JSON.parse(readFileSync(resolve(ROOT, rel), "utf8")) as T;

describe("Phase P2 (E1.3 ECOSTRESS/Landsat LST + ERA5 ObsChecks)", () => {
  it("keeps 100% EN/AR string key parity", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(ar).sort());
  });

  it("ships obs_checks with O/E provenance tags on Kansas and Ukraine FieldCalendars", () => {
    for (const [regionId, expectedCals, minLst] of [
      ["ks_t14slh", 200, 150],
      ["ua_central_t36uvu", 120, 120],
    ] as const) {
      const idx = readPackJson<RegionIndex>(`packs/demo/${regionId}/index.json`);
      expect(idx.fields).toHaveLength(expectedCals);
      let lstCount = 0;
      let eraCount = 0;
      for (const f of idx.fields) {
        const cal = readPackJson<FieldCalendar>(`packs/demo/${regionId}/${f.field_id}.calendar.json`);
        const pub = readPackJson<FieldCalendar>(`app/public/packs/${regionId}/${f.field_id}.calendar.json`);
        expect(pub.obs_checks).toEqual(cal.obs_checks);
        expect(cal.obs_checks).toBeTruthy();
        if (cal.obs_checks?.lst_heat) {
          expect(cal.obs_checks.lst_heat.tag).toBe("O");
          lstCount += 1;
        }
        if (cal.obs_checks?.extreme_rain_era5) {
          expect(cal.obs_checks.extreme_rain_era5.tag).toBe("E");
          eraCount += 1;
        }
      }
      expect(lstCount).toBeGreaterThanOrEqual(minLst);
      expect(eraCount).toBe(expectedCals);
    }
  });

  it("renders ObservedChecks table with O/E tags and scale badges in EN and AR", () => {
    const idx = readPackJson<RegionIndex>("packs/demo/ua_central_t36uvu/index.json");
    const sampleCal = readPackJson<FieldCalendar>(
      `packs/demo/ua_central_t36uvu/${idx.fields[0].field_id}.calendar.json`,
    );
    expect(OBS_CHECK_KEYS).toEqual(["lst_heat", "extreme_rain_era5"]);

    const prevLocale = "en" as const;
    setLocale("en");
    const htmlEn = renderToStaticMarkup(createElement(ObservedChecks, { cal: sampleCal }));
    expect(htmlEn).toContain("Observed thermal &amp; rainfall checks");
    expect(htmlEn).toContain("Landsat LST &gt; 35 °C");
    expect(htmlEn).toContain("ERA5 extreme rain (&gt; q99)");
    expect(htmlEn).toContain("flag-fine");
    expect(htmlEn).toContain("flag-coarse");
    expect(htmlEn).toContain(">O<");
    expect(htmlEn).toContain(">E<");

    setLocale("ar");
    const htmlAr = renderToStaticMarkup(createElement(ObservedChecks, { cal: sampleCal }));
    expect(htmlAr).toContain("فحوصات الحرارة والأمطار المرصودة");
    expect(htmlAr).toContain("دقة 30 م / 100 م");
    expect(htmlAr).toContain("سياق خشن 0.25°");

    setLocale(prevLocale);
  });
});
