import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ComparePage } from "../src/ComparePage";
import { compareHref, parseCompareQuery, parseHash } from "../src/route";
import { cropName, getLocale, setLocale, t } from "../src/strings";
import ar from "../src/strings/ar.json";
import en from "../src/strings/en.json";
import type { RegionIndex } from "../src/types";

describe("bilingual i18n (EN / AR)", () => {
  it("keeps 100% key and placeholder parity between en.json and ar.json", () => {
    const enKeys = Object.keys(en).sort();
    const arKeys = Object.keys(ar).sort();
    expect(arKeys).toEqual(enKeys);

    for (const k of enKeys) {
      const enVars = [...en[k as keyof typeof en].matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
      const arVars = [...ar[k as keyof typeof ar].matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
      expect(arVars, `placeholder mismatch on ${k}`).toEqual(enVars);
    }
  });

  it("switches locales cleanly and restores EN default", () => {
    const prev = getLocale();
    try {
      setLocale("ar");
      expect(getLocale()).toBe("ar");
      expect(t("nav.compare")).toBe("المقارنة");
      expect(cropName("winter_wheat")).toBe("القمح الشتوي");

      setLocale("en");
      expect(getLocale()).toBe("en");
      expect(t("nav.compare")).toBe("Compare");
      expect(cropName("winter_wheat")).toBe("Winter wheat");
    } finally {
      setLocale(prev);
    }
  });
});

describe("Compare view routing and SSR", () => {
  it("parses and builds #/<region>/compare?a=...&b=... URLs without breaking RegionRoute", () => {
    const href = compareHref("ks_t14slh", "field_aaa", "field_bbb");
    expect(href).toBe("#/ks_t14slh/compare?a=field_aaa&b=field_bbb");
    const r = parseHash(href);
    expect(r.regionId).toBe("ks_t14slh");
    expect(r.page).toBe("compare");
    expect(r.fieldId).toBeNull();
    expect(parseCompareQuery(href)).toEqual({ a: "field_aaa", b: "field_bbb" });
  });

  it("renders ComparePage selectors and headings cleanly", () => {
    const index: RegionIndex = {
      schema_version: "1.0",
      region_id: "ks_t14slh",
      name: "Kansas",
      tier: 1,
      bbox_lonlat: [-101.5, 39.0, -100.5, 40.0],
      basemap: null,
      data_as_of: "2024-12-31",
      fields: [
        {
          field_id: "aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111",
          centroid_lonlat: [-101.0, 39.3],
          area_ha: 42.5,
          current_crop: "winter_wheat",
          current_sequence: ["winter_wheat", "sorghum", "fallow"],
          top_grade: "B",
        },
        {
          field_id: "bbbb2222bbbb2222bbbb2222bbbb2222bbbb2222",
          centroid_lonlat: [-101.1, 39.4],
          area_ha: 65.0,
          current_crop: "maize",
          current_sequence: ["maize", "soybean", "winter_wheat"],
          top_grade: "B",
        },
      ],
    };

    const html = renderToStaticMarkup(createElement(ComparePage, { index }));
    expect(html).toContain(t("compare.heading"));
    expect(html).toContain(t("compare.fieldA"));
    expect(html).toContain(t("compare.fieldB"));
    expect(html).toContain("42.5 ha");
    expect(html).toContain("65.0 ha");
  });
});
