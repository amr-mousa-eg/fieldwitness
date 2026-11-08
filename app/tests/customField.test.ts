import { describe, expect, it } from "vitest";
import {
  COVERAGE_ERROR_MESSAGE,
  FAR_FIELD_DISCLAIMER,
  findNearestAnalysedField,
  generateCsvTemplate,
  getRecentHarvestYears,
  haversineDistanceKm,
  isInsideKansasTile,
  NEAREST_FIELD_DISCLAIMER,
  NEAREST_FIELD_LABEL,
  parseCsvInput,
  PRESET_LOCATIONS,
  SOIL_TEST_DISCLAIMER,
  SUPPORTED_AREAS_TEXT,
} from "../src/customField";
import type { FieldSummary } from "../src/types";

describe("customField coverage checker", () => {
  it("recognizes supported locations inside Kansas T14SLH tile", () => {
    // Garden City, KS (lon: -100.8727, lat: 37.9717)
    expect(isInsideKansasTile(-100.8727, 37.9717)).toBe(true);
    // Scott City, KS (lon: -100.9074, lat: 38.4828)
    expect(isInsideKansasTile(-100.9074, 38.4828)).toBe(true);
  });

  it("rejects locations outside the tile footprint", () => {
    // Cimarron, KS is south of the tile boundary (~37.81°N)
    expect(isInsideKansasTile(-100.3482, 37.8078)).toBe(false);
    // Cairo, Egypt
    expect(isInsideKansasTile(31.2357, 30.0444)).toBe(false);
    // Dodge City, KS
    expect(isInsideKansasTile(-100.0171, 37.7528)).toBe(false);
    // Paris, France
    expect(isInsideKansasTile(2.3522, 48.8566)).toBe(false);
  });

  it("handles non-numeric or NaN coordinates safely", () => {
    expect(isInsideKansasTile(NaN, 38.0)).toBe(false);
    expect(isInsideKansasTile(-100.5, NaN)).toBe(false);
  });

  it("verifies every preset location matches its declared coverage status", () => {
    for (const preset of PRESET_LOCATIONS) {
      const computed = isInsideKansasTile(preset.longitude, preset.latitude);
      expect(computed).toBe(preset.is_supported);
    }
  });

  it("has exact required error and disclaimer strings", () => {
    expect(COVERAGE_ERROR_MESSAGE).toBe("We apologize, but this location is not currently supported.");
    expect(SUPPORTED_AREAS_TEXT).toBe("Currently supported areas: Kansas High Plains (HLS Tile T14SLH).");
    expect(NEAREST_FIELD_LABEL).toBe("Nearest analysed field — your field is not analysed yet");
    expect(NEAREST_FIELD_DISCLAIMER).toBe(
      "This is the closest field we have analysed, measured by distance only. Its soil, slope, history and management may differ from yours."
    );
    expect(FAR_FIELD_DISCLAIMER).toBe("This field is far from yours; treat it as a general example only.");
    expect(SOIL_TEST_DISCLAIMER).toBe("Saved for future analysis — not used in version 0");
  });
});

describe("customField harvest years calculation", () => {
  it("computes 2026, 2025, 2024 for November 2026", () => {
    const nov2026 = new Date(2026, 10, 8); // month 10 is Nov (0-indexed)
    expect(getRecentHarvestYears(nov2026)).toEqual([2026, 2025, 2024]);
  });

  it("computes previous 3 years if before harvest season end", () => {
    const march2026 = new Date(2026, 2, 15); // month 2 is March
    expect(getRecentHarvestYears(march2026)).toEqual([2025, 2024, 2023]);
  });
});

describe("customField distance and nearest analysed field", () => {
  it("computes haversine distance accurately", () => {
    // Garden City to Scott City is approx 57 km
    const d = haversineDistanceKm(37.9717, -100.8727, 38.4828, -100.9074);
    expect(d).toBeGreaterThan(50);
    expect(d).toBeLessThan(65);
  });

  it("finds the nearest pilot field and applies distance warnings", () => {
    const mockFields: FieldSummary[] = [
      {
        field_id: "close_field",
        geometry_wkt: "POLYGON ((-100.88 37.97, -100.86 37.97, -100.86 37.98, -100.88 37.98, -100.88 37.97))",
        area_ha: 50.0,
        current_sequence: ["maize"],
        top_option_id: "opt1",
        top_grade: "B",
      },
      {
        field_id: "far_field",
        geometry_wkt: "POLYGON ((-100.10 38.80, -100.08 38.80, -100.08 38.82, -100.10 38.82, -100.10 38.80))",
        area_ha: 60.0,
        current_sequence: ["winter_wheat"],
        top_option_id: "opt2",
        top_grade: "C",
      },
    ];

    // Point close to close_field
    const resNear = findNearestAnalysedField(37.975, -100.87, mockFields);
    expect(resNear).not.toBeNull();
    expect(resNear?.field.field_id).toBe("close_field");
    expect(resNear?.isFar).toBe(false);
    expect(resNear?.farDisclaimer).toBeNull();
    expect(resNear?.label).toBe(NEAREST_FIELD_LABEL);
    expect(resNear?.disclaimer).toBe(NEAREST_FIELD_DISCLAIMER);

    // Point far (> 10 km) from all fields
    const resFar = findNearestAnalysedField(37.5, -100.87, mockFields);
    expect(resFar).not.toBeNull();
    expect(resFar?.isFar).toBe(true);
    expect(resFar?.farDisclaimer).toBe(FAR_FIELD_DISCLAIMER);
  });
});

describe("customField CSV generator and parser", () => {
  it("generates CSV template with UTF-8 BOM and correct headers", () => {
    const nov2026 = new Date(2026, 10, 8);
    const csv = generateCsvTemplate(nov2026);
    expect(csv.charCodeAt(0)).toBe(0xfeff); // UTF-8 BOM
    expect(csv).toContain("question,answer,help");
    expect(csv).toContain("latitude");
    expect(csv).toContain("crop_2026");
    expect(csv).toContain("crop_2025");
    expect(csv).toContain("crop_2024");
  });

  it("successfully parses valid CSV template round-trip", () => {
    const nov2026 = new Date(2026, 10, 8);
    const csv = generateCsvTemplate(nov2026);
    const parsed = parseCsvInput(csv, nov2026);
    expect(parsed.errors).toEqual([]);
    expect(parsed.data).not.toBeNull();
    expect(parsed.data?.latitude).toBeCloseTo(37.9717);
    expect(parsed.data?.longitude).toBeCloseTo(-100.8727);
    expect(parsed.data?.irrigation.is_irrigated).toBe("yes");
    expect(parsed.data?.irrigation.amount).toBe(10);
    expect(parsed.data?.irrigation.unit).toBe("in");
  });

  it("reports clear error on invalid latitude/longitude", () => {
    const badCsv = `question,answer,help\nlatitude,"abc","desc"\nlongitude,"-100.5","desc"`;
    const parsed = parseCsvInput(badCsv);
    expect(parsed.errors.length).toBeGreaterThan(0);
    expect(parsed.errors[0]).toContain("Invalid latitude");
    expect(parsed.data).toBeNull();
  });

  it("accepts 'unknown' / 'I don't know' for all items", () => {
    const unknownCsv = `question,answer,help
latitude,"37.9717","help"
longitude,"-100.8727","help"
crop_2026,"I don't know","help"
sowing_2026,"unknown","help"
irrigated,"unknown","help"
soil_organic_matter_pct,"unknown","help"
soil_ph,"n/a","help"`;
    const parsed = parseCsvInput(unknownCsv, new Date(2026, 10, 8));
    expect(parsed.errors).toEqual([]);
    expect(parsed.data).not.toBeNull();
    expect(parsed.data?.seasons[0].crop).toBe("unknown");
    expect(parsed.data?.irrigation.is_irrigated).toBe("unknown");
    expect(parsed.data?.soil_tests.organic_matter_pct).toBeNull();
  });
});
