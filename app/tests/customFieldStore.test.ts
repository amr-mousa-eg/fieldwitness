import { describe, expect, it } from "vitest";
import { getDefaultFormData } from "../src/customField";
import {
  clearAllCustomFields,
  convertFormToRecord,
  type CustomFieldRecord,
  deleteCustomField,
  exportFieldsAsJson,
  importFieldsFromJson,
  loadSavedFields,
  saveCustomField,
  type StorageLike,
} from "../src/customFieldStore";

const mem = (): StorageLike & { m: Map<string, string> } => {
  const m = new Map<string, string>();
  return {
    m,
    getItem: (k) => m.get(k) ?? null,
    setItem: (k, v) => void m.set(k, v),
    removeItem: (k) => void m.delete(k),
  };
};

const throwing: StorageLike = {
  getItem: () => {
    throw new Error("storage error");
  },
  setItem: () => {
    throw new Error("quota exceeded");
  },
  removeItem: () => {
    throw new Error("permission denied");
  },
};

describe("customFieldStore device storage", () => {
  it("converts form data to tagged immutable record with tag E and schema version 1.0", () => {
    const form = getDefaultFormData(new Date(2026, 10, 8));
    form.name = "Test Field 1";
    form.latitude = 37.9717;
    form.longitude = -100.8727;
    form.irrigation.is_irrigated = "yes";
    form.irrigation.amount = 10;
    form.irrigation.unit = "in"; // 10 inches

    const record = convertFormToRecord(form, true);
    expect(record.source_tag).toBe("E");
    expect(record.schema_version).toBe("1.0");
    expect(record.name).toBe("Test Field 1");
    expect(record.is_supported).toBe(true);
    expect(record.coordinates.latitude).toBe(37.9717);
    expect(record.coordinates.longitude).toBe(-100.8727);
    // 10 inches converted to mm: 254.0 mm
    expect(record.irrigation.amount_mm).toBe(254);
  });

  it("round-trips saving, loading, and updating custom fields in storage", () => {
    const s = mem();
    const form = getDefaultFormData(new Date(2026, 10, 8));
    form.name = "Quarter A";
    form.latitude = 37.97;
    form.longitude = -100.87;

    const rec1 = convertFormToRecord(form, true, "f1");
    expect(saveCustomField(rec1, s)).toBe(true);

    const loaded1 = loadSavedFields(s);
    expect(loaded1.length).toBe(1);
    expect(loaded1[0].id).toBe("f1");
    expect(loaded1[0].name).toBe("Quarter A");

    // Add second field
    form.name = "Quarter B";
    const rec2 = convertFormToRecord(form, true, "f2");
    expect(saveCustomField(rec2, s)).toBe(true);

    const loaded2 = loadSavedFields(s);
    expect(loaded2.length).toBe(2);

    // Delete first field
    expect(deleteCustomField("f1", s)).toBe(true);
    const loaded3 = loadSavedFields(s);
    expect(loaded3.length).toBe(1);
    expect(loaded3[0].id).toBe("f2");

    // Clear all fields
    expect(clearAllCustomFields(s)).toBe(true);
    expect(loadSavedFields(s).length).toBe(0);
  });

  it("exports and imports fields as JSON", () => {
    const s1 = mem();
    const form = getDefaultFormData(new Date(2026, 10, 8));
    form.name = "Export Field";
    form.latitude = 38.0;
    form.longitude = -100.5;
    const rec = convertFormToRecord(form, true, "f_exp");
    saveCustomField(rec, s1);

    const exportedJson = exportFieldsAsJson(s1);
    expect(exportedJson).toContain('"schema_version": "1.0"');
    expect(exportedJson).toContain('"source_tag": "E"');
    expect(exportedJson).toContain("Export Field");

    // Import into a new store
    const s2 = mem();
    const importRes = importFieldsFromJson(exportedJson, s2);
    expect(importRes.errors).toEqual([]);
    expect(importRes.imported).toBe(1);

    const loadedFromS2 = loadSavedFields(s2);
    expect(loadedFromS2.length).toBe(1);
    expect(loadedFromS2[0].name).toBe("Export Field");
  });

  it("handles storage exceptions gracefully", () => {
    // Reading or writing when storage throws does not crash
    expect(loadSavedFields(throwing)).toEqual([]);
    const form = getDefaultFormData(new Date(2026, 10, 8));
    const rec = convertFormToRecord(form, false, "f_throw");
    expect(saveCustomField(rec, throwing)).toBe(false);
    expect(deleteCustomField("f_throw", throwing)).toBe(false);
    expect(clearAllCustomFields(throwing)).toBe(false);
  });
});
