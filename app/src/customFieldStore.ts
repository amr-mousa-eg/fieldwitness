import type { CustomFieldFormData } from "./customField";
import { SOIL_TEST_DISCLAIMER } from "./customField";
import type { Priorities } from "./rank";

export const CUSTOM_FIELDS_STORAGE_KEY = "fw.custom_fields.v1";

export interface CustomFieldRecord {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  source_tag: "E"; // farmer-entered data (CLAUDE.md)
  schema_version: "1.0";
  coordinates: {
    latitude: number;
    longitude: number;
  };
  is_supported: boolean;
  seasons: {
    harvest_year: number;
    crop: string;
    sowing: string;
  }[];
  irrigation: {
    is_irrigated: "yes" | "no" | "unknown";
    amount_mm: number | null;
    input_unit: "in" | "mm";
  };
  soil_tests: {
    organic_matter_pct: number | null;
    ph: number | null;
    cec: number | null;
    notes: string;
    disclaimer: typeof SOIL_TEST_DISCLAIMER;
  };
  priorities: Priorities;
  constraints: {
    can_sell: string[];
    cant_grow: string[];
    water_cap_mm: number | null;
    notes: string;
  };
}

export interface StorageLike {
  getItem(k: string): string | null;
  setItem(k: string, v: string): void;
  removeItem(k: string): void;
}

// In-memory fallback if storage access throws or is blocked
let memoryStore: Record<string, string> = {};

export function resetMemoryStoreForTesting(): void {
  memoryStore = {};
}

export function defaultStorage(): StorageLike {
  try {
    if (typeof localStorage !== "undefined") {
      // Test read/write
      const testKey = "__fw_test__";
      localStorage.setItem(testKey, "1");
      localStorage.removeItem(testKey);
      return localStorage;
    }
  } catch {
    // fallback below
  }
  return {
    getItem: (k: string) => memoryStore[k] ?? null,
    setItem: (k: string, v: string) => {
      memoryStore[k] = v;
    },
    removeItem: (k: string) => {
      delete memoryStore[k];
    },
  };
}

export function loadSavedFields(store: StorageLike = defaultStorage()): CustomFieldRecord[] {
  try {
    const raw = store.getItem(CUSTOM_FIELDS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (item): item is CustomFieldRecord =>
        Boolean(
          item &&
            typeof item === "object" &&
            item.schema_version === "1.0" &&
            item.source_tag === "E" &&
            typeof item.id === "string" &&
            item.coordinates &&
            typeof item.coordinates.latitude === "number" &&
            typeof item.coordinates.longitude === "number"
        )
    );
  } catch {
    return [];
  }
}

export function saveCustomField(
  record: CustomFieldRecord,
  store: StorageLike = defaultStorage()
): boolean {
  try {
    const current = loadSavedFields(store);
    const existingIdx = current.findIndex((f) => f.id === record.id);
    const updated = [...current];
    if (existingIdx >= 0) {
      updated[existingIdx] = { ...record, updated_at: new Date().toISOString() };
    } else {
      updated.push(record);
    }
    store.setItem(CUSTOM_FIELDS_STORAGE_KEY, JSON.stringify(updated));
    return true;
  } catch {
    return false;
  }
}

export function deleteCustomField(
  id: string,
  store: StorageLike = defaultStorage()
): boolean {
  try {
    const current = loadSavedFields(store);
    const filtered = current.filter((f) => f.id !== id);
    store.setItem(CUSTOM_FIELDS_STORAGE_KEY, JSON.stringify(filtered));
    return true;
  } catch {
    return false;
  }
}

export function clearAllCustomFields(store: StorageLike = defaultStorage()): boolean {
  try {
    store.removeItem(CUSTOM_FIELDS_STORAGE_KEY);
    return true;
  } catch {
    return false;
  }
}

/** Converts form state into an immutable, versioned, tagged record */
export function convertFormToRecord(
  form: CustomFieldFormData,
  isSupported: boolean,
  existingId?: string
): CustomFieldRecord {
  const now = new Date().toISOString();
  const id = existingId ?? `field_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;

  // Convert irrigation inches to mm: 1 inch = 25.4 mm
  let amountMm: number | null = null;
  if (form.irrigation.amount !== null && !isNaN(form.irrigation.amount)) {
    amountMm =
      form.irrigation.unit === "in"
        ? Math.round(form.irrigation.amount * 25.4 * 10) / 10
        : form.irrigation.amount;
  }

  return {
    id,
    name: form.name.trim() || `My Field (${form.latitude?.toFixed(4)}, ${form.longitude?.toFixed(4)})`,
    created_at: now,
    updated_at: now,
    source_tag: "E",
    schema_version: "1.0",
    coordinates: {
      latitude: form.latitude ?? 0,
      longitude: form.longitude ?? 0,
    },
    is_supported: isSupported,
    seasons: form.seasons.map((s) => ({
      harvest_year: s.harvest_year,
      crop: s.crop,
      sowing: s.sowing,
    })),
    irrigation: {
      is_irrigated: form.irrigation.is_irrigated,
      amount_mm: amountMm,
      input_unit: form.irrigation.unit,
    },
    soil_tests: {
      organic_matter_pct: form.soil_tests.organic_matter_pct,
      ph: form.soil_tests.ph,
      cec: form.soil_tests.cec,
      notes: form.soil_tests.notes,
      disclaimer: SOIL_TEST_DISCLAIMER,
    },
    priorities: { ...form.priorities },
    constraints: {
      can_sell: [...form.constraints.can_sell],
      cant_grow: [...form.constraints.cant_grow],
      water_cap_mm: form.constraints.water_cap_mm,
      notes: form.constraints.notes,
    },
  };
}

export function exportFieldsAsJson(store: StorageLike = defaultStorage()): string {
  const fields = loadSavedFields(store);
  return JSON.stringify(
    {
      exported_at: new Date().toISOString(),
      schema_version: "1.0",
      source_tag: "E",
      count: fields.length,
      fields,
    },
    null,
    2
  );
}

export function importFieldsFromJson(
  jsonText: string,
  store: StorageLike = defaultStorage()
): { imported: number; errors: string[] } {
  try {
    const parsed = JSON.parse(jsonText);
    const list: unknown[] = Array.isArray(parsed) ? parsed : Array.isArray(parsed.fields) ? parsed.fields : [];
    if (!list.length) {
      return { imported: 0, errors: ["No valid custom field entries found in file."] };
    }

    const current = loadSavedFields(store);
    const currentMap = new Map(current.map((f) => [f.id, f]));
    let count = 0;

    for (const item of list) {
      if (
        item &&
        typeof item === "object" &&
        (item as CustomFieldRecord).schema_version === "1.0" &&
        (item as CustomFieldRecord).coordinates &&
        typeof (item as CustomFieldRecord).coordinates.latitude === "number" &&
        typeof (item as CustomFieldRecord).coordinates.longitude === "number"
      ) {
        const record = item as CustomFieldRecord;
        currentMap.set(record.id, record);
        count++;
      }
    }

    const merged = Array.from(currentMap.values());
    store.setItem(CUSTOM_FIELDS_STORAGE_KEY, JSON.stringify(merged));
    return { imported: count, errors: [] };
  } catch (err) {
    return { imported: 0, errors: [`JSON parsing error: ${(err as Error).message}`] };
  }
}
