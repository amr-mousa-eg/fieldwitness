import { DEFAULT_PRIORITIES, type Priorities, PRIORITY_KEYS } from "./rank";
import type { FieldSummary } from "./types";
import { wktToGeometry } from "./wkt";

/**
 * Exact 4-corner footprint polygon of HLS MGRS tile T14SLH (UTM Zone 14N: EPSG:32614).
 * Coordinates transformed from UTM grid origin and bounds:
 * UL: (300000, 4300020) -> (-101.303931, 38.826273)
 * UR: (409800, 4300020) -> (-100.039384, 38.844374)
 * LR: (409800, 4190220) -> (-100.025337, 37.854978)
 * LL: (300000, 4190220) -> (-101.272818, 37.837503)
 *
 * Ordered counter-clockwise/clockwise closed ring of [lon, lat].
 */
export const KANSAS_T14SLH_FOOTPRINT: [number, number][] = [
  [-101.303931, 38.826273], // Upper-Left [lon, lat]
  [-100.039384, 38.844374], // Upper-Right
  [-100.025337, 37.854978], // Lower-Right
  [-101.272818, 37.837503], // Lower-Left
];

/**
 * Point-in-polygon ray-casting test.
 * Verifies whether coordinates fall inside the true tilted quadrilateral footprint of tile T14SLH,
 * preventing false positives from rectangular bounding box corners.
 */
export function isInsideKansasTile(lon: number, lat: number): boolean {
  if (typeof lon !== "number" || typeof lat !== "number" || isNaN(lon) || isNaN(lat)) {
    return false;
  }
  const polygon = KANSAS_T14SLH_FOOTPRINT;
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i][0];
    const yi = polygon[i][1];
    const xj = polygon[j][0];
    const yj = polygon[j][1];
    const intersect = yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

/** Exact string mandated for out-of-area locations */
export const COVERAGE_ERROR_MESSAGE = "We apologize, but this location is not currently supported.";
export const SUPPORTED_AREAS_TEXT = "Currently supported areas: Kansas High Plains (HLS Tile T14SLH).";

export const NEAREST_FIELD_LABEL = "Nearest analysed field — your field is not analysed yet";
export const NEAREST_FIELD_DISCLAIMER =
  "This is the closest field we have analysed, measured by distance only. Its soil, slope, history and management may differ from yours.";
export const FAR_FIELD_DISCLAIMER = "This field is far from yours; treat it as a general example only.";
export const SOIL_TEST_DISCLAIMER = "Saved for future analysis — not used in version 0";

export interface PresetLocation {
  id: string;
  label: string;
  latitude: number;
  longitude: number;
  is_supported: boolean;
}

export const PRESET_LOCATIONS: PresetLocation[] = [
  {
    id: "garden-city",
    label: "Garden City, KS",
    latitude: 37.9717,
    longitude: -100.8727,
    is_supported: true,
  },
  {
    id: "scott-city",
    label: "Scott City, KS",
    latitude: 38.4828,
    longitude: -100.9074,
    is_supported: true,
  },
  {
    id: "cairo-demo",
    label: "Cairo, Egypt (demo unsupported)",
    latitude: 30.0444,
    longitude: 31.2357,
    is_supported: false,
  },
];

/**
 * Computes past 3 completed harvest years from the reference date (PLAN.md T2.2).
 * Kansas summer crop harvest completes in Oct/Nov; in Nov 2026, returns [2026, 2025, 2024].
 */
export function getRecentHarvestYears(now: Date = new Date()): [number, number, number] {
  const currentYear = now.getFullYear();
  // If month is October (9) or later (0-indexed), current calendar year's harvest is completed.
  const lastHarvestYear = now.getMonth() >= 9 ? currentYear : currentYear - 1;
  return [lastHarvestYear, lastHarvestYear - 1, lastHarvestYear - 2];
}

export const KANSAS_CROPS = [
  { id: "winter_wheat", label: "Winter Wheat" },
  { id: "maize", label: "Corn / Maize" },
  { id: "sorghum", label: "Sorghum" },
  { id: "fallow", label: "Fallow / Idle" },
  { id: "cover_crop", label: "Cover Crop" },
  { id: "other", label: "Other Crop" },
  { id: "unknown", label: "I don't know / Not sure" },
] as const;

export const SOWING_WINDOWS = [
  { id: "early_spring", label: "Early Spring (Mar – Apr)" },
  { id: "late_spring", label: "Late Spring (May – Jun)" },
  { id: "early_fall", label: "Early Fall (Sep – Oct)" },
  { id: "late_fall", label: "Late Fall (Nov)" },
  { id: "other", label: "Other / Custom" },
  { id: "unknown", label: "I don't know" },
] as const;

export interface CustomFieldSeasonData {
  harvest_year: number;
  crop: string;
  sowing: string;
}

export interface CustomFieldFormData {
  name: string;
  latitude: number | null;
  longitude: number | null;
  seasons: CustomFieldSeasonData[];
  irrigation: {
    is_irrigated: "yes" | "no" | "unknown";
    amount: number | null;
    unit: "in" | "mm";
  };
  soil_tests: {
    organic_matter_pct: number | null;
    ph: number | null;
    cec: number | null;
    notes: string;
  };
  priorities: Priorities;
  constraints: {
    can_sell: string[];
    cant_grow: string[];
    water_cap_mm: number | null;
    notes: string;
  };
}

export function getDefaultFormData(now: Date = new Date()): CustomFieldFormData {
  const years = getRecentHarvestYears(now);
  return {
    name: "",
    latitude: null,
    longitude: null,
    seasons: [
      { harvest_year: years[0], crop: "unknown", sowing: "unknown" },
      { harvest_year: years[1], crop: "unknown", sowing: "unknown" },
      { harvest_year: years[2], crop: "unknown", sowing: "unknown" },
    ],
    irrigation: {
      is_irrigated: "unknown",
      amount: null,
      unit: "in",
    },
    soil_tests: {
      organic_matter_pct: null,
      ph: null,
      cec: null,
      notes: "",
    },
    priorities: { ...DEFAULT_PRIORITIES },
    constraints: {
      can_sell: ["maize", "winter_wheat", "sorghum"],
      cant_grow: [],
      water_cap_mm: null,
      notes: "",
    },
  };
}

/** Haversine formula for spherical distance in km between two coordinate pairs */
export function haversineDistanceKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371.0;
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/** Extract midpoint coordinate [lon, lat] from a field WKT geometry */
export function getFieldCentroid(geometryWkt: string): [number, number] {
  const geom = wktToGeometry(geometryWkt);
  let w = Infinity,
    s = Infinity,
    e = -Infinity,
    n = -Infinity;
  const rings = geom.type === "Polygon" ? geom.coordinates : geom.coordinates.flat();
  for (const ring of rings) {
    for (const [x, y] of ring) {
      if (x < w) w = x;
      if (x > e) e = x;
      if (y < s) s = y;
      if (y > n) n = y;
    }
  }
  return [(w + e) / 2, (s + n) / 2];
}

export interface NearestFieldResult {
  field: FieldSummary;
  distanceKm: number;
  fieldNumber: number;
  fieldCentroid: [number, number];
  isFar: boolean;
  label: string;
  disclaimer: string;
  farDisclaimer: string | null;
}

/**
 * Find the nearest analysed pilot field by distance only.
 * Always surfaces explicit mandatory disclaimers and handles > 10 km warning.
 */
export function findNearestAnalysedField(
  lat: number,
  lon: number,
  fields: FieldSummary[]
): NearestFieldResult | null {
  if (!fields.length || typeof lat !== "number" || typeof lon !== "number" || isNaN(lat) || isNaN(lon)) {
    return null;
  }

  let bestField: FieldSummary | null = null;
  let bestIdx = -1;
  let minDistance = Infinity;
  let bestCentroid: [number, number] = [0, 0];

  for (let i = 0; i < fields.length; i++) {
    const f = fields[i];
    try {
      const centroid = getFieldCentroid(f.geometry_wkt);
      const d = haversineDistanceKm(lat, lon, centroid[1], centroid[0]);
      if (d < minDistance) {
        minDistance = d;
        bestField = f;
        bestIdx = i;
        bestCentroid = centroid;
      }
    } catch {
      // Ignore unparseable WKT
    }
  }

  if (!bestField) return null;

  const isFar = minDistance > 10.0;
  return {
    field: bestField,
    distanceKm: Math.round(minDistance * 10) / 10,
    fieldNumber: bestIdx + 1,
    fieldCentroid: bestCentroid,
    isFar,
    label: NEAREST_FIELD_LABEL,
    disclaimer: NEAREST_FIELD_DISCLAIMER,
    farDisclaimer: isFar ? FAR_FIELD_DISCLAIMER : null,
  };
}

/**
 * Generates downloadable key-value CSV template with UTF-8 BOM (\uFEFF)
 * allowing farmers to fill in records offline.
 */
export function generateCsvTemplate(now: Date = new Date()): string {
  const years = getRecentHarvestYears(now);
  const rows = [
    ["latitude", "37.9717", "Decimal latitude (e.g. 37.9717 for Garden City area)"],
    ["longitude", "-100.8727", "Decimal longitude (e.g. -100.8727)"],
    ["field_name", "North Quarter", "Optional name or label for your field"],
    [
      `crop_${years[0]}`,
      "winter_wheat",
      `Crop grown in last season (${years[0]}): winter_wheat, maize, sorghum, fallow, cover_crop, other, or unknown`,
    ],
    [`sowing_${years[0]}`, "early_fall", "Sowing window (early_fall, late_fall, early_spring, late_spring, or unknown)"],
    [`crop_${years[1]}`, "maize", `Crop grown 2 seasons ago (${years[1]}), or unknown`],
    [`sowing_${years[1]}`, "late_spring", "Sowing window, or unknown"],
    [`crop_${years[2]}`, "fallow", `Crop grown 3 seasons ago (${years[2]}), or unknown`],
    [`sowing_${years[2]}`, "unknown", "Sowing window, or unknown"],
    ["irrigated", "yes", "Can this field be irrigated? yes / no / unknown"],
    ["irrigation_amount", "10 in", "Annual irrigation amount (e.g. '10 in' or '254 mm'), or unknown"],
    ["soil_organic_matter_pct", "2.1", "Soil organic matter % (saved for future analysis), or unknown"],
    ["soil_ph", "7.2", "Soil pH (saved for future analysis), or unknown"],
    ["soil_cec", "18.5", "Cation exchange capacity meq/100g, or unknown"],
    ["priority_water", "3", "Priority for saving water: 0=Ignore, 1=Low, 2=Medium, 3=High"],
    ["priority_bare", "2", "Priority for fewer bare months: 0=Ignore, 1=Low, 2=Medium, 3=High"],
    ["priority_bad_year", "3", "Priority for resilience in bad years: 0=Ignore, 1=Low, 2=Medium, 3=High"],
    ["priority_erosion", "2", "Priority for reducing erosion: 0=Ignore, 1=Low, 2=Medium, 3=High"],
    ["priority_legume", "1", "Priority for nitrogen-fixing crops: 0=Ignore, 1=Low, 2=Medium, 3=High"],
    ["priority_residue", "2", "Priority for organic matter input: 0=Ignore, 1=Low, 2=Medium, 3=High"],
    ["crops_can_sell", "maize, winter_wheat, sorghum", "Crops you can sell at market, comma-separated"],
    ["crops_cant_grow", "", "Crops you cannot plant or harvest (e.g. lack of machinery)"],
    ["annual_water_cap_mm", "", "Annual water allocation cap in mm (optional)"],
    ["notes", "Deep silt loam soil with center pivot", "Any notes or constraints"],
  ];

  const escapeCsv = (str: string) => `"${str.replace(/"/g, '""')}"`;
  const header = "question,answer,help";
  const body = rows.map(([q, a, h]) => `${escapeCsv(q)},${escapeCsv(a)},${escapeCsv(h)}`).join("\r\n");

  // \uFEFF is UTF-8 Byte Order Mark for Excel compatibility
  return `\uFEFF${header}\r\n${body}\r\n`;
}

/**
 * Validates and parses uploaded key-value CSV file.
 * Returns clear line-by-line / field-by-field error messages if invalid.
 */
export function parseCsvInput(
  csvText: string,
  now: Date = new Date()
): { data: CustomFieldFormData | null; errors: string[] } {
  const errors: string[] = [];
  const years = getRecentHarvestYears(now);
  const formData = getDefaultFormData(now);

  // Strip BOM if present
  let cleanText = csvText;
  if (cleanText.charCodeAt(0) === 0xfeff) {
    cleanText = cleanText.slice(1);
  }

  const lines = cleanText.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  if (lines.length < 2) {
    errors.push("CSV file is empty or missing data rows.");
    return { data: null, errors };
  }

  // Parse lines considering quotes
  const parseRow = (line: string): string[] => {
    const res: string[] = [];
    let cur = "";
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (c === '"') {
        if (inQuotes && line[i + 1] === '"') {
          cur += '"';
          i++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (c === "," && !inQuotes) {
        res.push(cur.trim());
        cur = "";
      } else {
        cur += c;
      }
    }
    res.push(cur.trim());
    return res;
  };

  const kv: Record<string, string> = {};
  for (let lineNum = 1; lineNum <= lines.length; lineNum++) {
    const rawLine = lines[lineNum - 1];
    const parts = parseRow(rawLine);
    if (parts.length < 2) continue;
    const key = parts[0].toLowerCase().trim();
    const val = parts[1].trim();
    if (key === "question") continue; // skip header
    kv[key] = val;
  }

  // Parse Coordinates
  if (kv["latitude"]) {
    const latVal = kv["latitude"].toLowerCase();
    if (latVal !== "unknown" && latVal !== "i don't know") {
      const lat = parseFloat(kv["latitude"]);
      if (isNaN(lat) || lat < -90 || lat > 90) {
        errors.push(`Invalid latitude "${kv["latitude"]}". Expected decimal degrees between -90 and 90.`);
      } else {
        formData.latitude = lat;
      }
    }
  }

  if (kv["longitude"]) {
    const lonVal = kv["longitude"].toLowerCase();
    if (lonVal !== "unknown" && lonVal !== "i don't know") {
      const lon = parseFloat(kv["longitude"]);
      if (isNaN(lon) || lon < -180 || lon > 180) {
        errors.push(`Invalid longitude "${kv["longitude"]}". Expected decimal degrees between -180 and 180.`);
      } else {
        formData.longitude = lon;
      }
    }
  }

  if (kv["field_name"]) {
    formData.name = kv["field_name"];
  }

  // Parse Seasons
  const normalizeCrop = (c: string): string => {
    const lower = c.toLowerCase().trim();
    if (!lower || lower === "unknown" || lower === "i don't know" || lower === "n/a") return "unknown";
    if (lower.includes("wheat")) return "winter_wheat";
    if (lower.includes("corn") || lower.includes("maize")) return "maize";
    if (lower.includes("sorghum")) return "sorghum";
    if (lower.includes("fallow") || lower.includes("idle")) return "fallow";
    if (lower.includes("cover")) return "cover_crop";
    return "other";
  };

  for (let idx = 0; idx < 3; idx++) {
    const y = years[idx];
    const cropKey = `crop_${y}`;
    const sowingKey = `sowing_${y}`;
    if (kv[cropKey]) {
      formData.seasons[idx].crop = normalizeCrop(kv[cropKey]);
    }
    if (kv[sowingKey]) {
      formData.seasons[idx].sowing = kv[sowingKey];
    }
  }

  // Parse Irrigation
  if (kv["irrigated"]) {
    const irr = kv["irrigated"].toLowerCase();
    if (irr === "yes" || irr === "true" || irr === "y") formData.irrigation.is_irrigated = "yes";
    else if (irr === "no" || irr === "false" || irr === "n") formData.irrigation.is_irrigated = "no";
    else formData.irrigation.is_irrigated = "unknown";
  }

  if (kv["irrigation_amount"]) {
    const amtStr = kv["irrigation_amount"].toLowerCase().trim();
    if (amtStr && amtStr !== "unknown" && amtStr !== "none") {
      const match = amtStr.match(/^([\d.]+)\s*(in|inch|inches|mm)?$/);
      if (match) {
        const val = parseFloat(match[1]);
        const unit = match[2]?.startsWith("in") ? "in" : "mm";
        formData.irrigation.amount = val;
        formData.irrigation.unit = unit;
      } else {
        errors.push(`Could not parse irrigation amount "${kv["irrigation_amount"]}". Use e.g. "10 in" or "250 mm".`);
      }
    }
  }

  // Parse Soil tests
  const parseNum = (val: string | undefined): number | null => {
    if (!val || val.toLowerCase() === "unknown" || val.toLowerCase() === "n/a") return null;
    const n = parseFloat(val);
    return isNaN(n) ? null : n;
  };

  formData.soil_tests.organic_matter_pct = parseNum(kv["soil_organic_matter_pct"]);
  formData.soil_tests.ph = parseNum(kv["soil_ph"]);
  formData.soil_tests.cec = parseNum(kv["soil_cec"]);

  // Parse Priorities
  for (const k of PRIORITY_KEYS) {
    const prioKey = `priority_${k === "badYear" ? "bad_year" : k}`;
    if (kv[prioKey]) {
      const n = parseInt(kv[prioKey], 10);
      if (!isNaN(n) && n >= 0 && n <= 3) {
        formData.priorities[k] = n;
      }
    }
  }

  // Parse Constraints
  if (kv["crops_can_sell"]) {
    formData.constraints.can_sell = kv["crops_can_sell"]
      .split(",")
      .map((s) => normalizeCrop(s))
      .filter((c) => c !== "unknown");
  }

  if (kv["crops_cant_grow"]) {
    formData.constraints.cant_grow = kv["crops_cant_grow"]
      .split(",")
      .map((s) => normalizeCrop(s))
      .filter((c) => c !== "unknown");
  }

  if (kv["annual_water_cap_mm"]) {
    formData.constraints.water_cap_mm = parseNum(kv["annual_water_cap_mm"]);
  }

  if (kv["notes"]) {
    formData.constraints.notes = kv["notes"];
  }

  return {
    data: errors.length > 0 ? null : formData,
    errors,
  };
}
