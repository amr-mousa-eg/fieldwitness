/**
 * Season keys the rotation model simulates:
 * - Default / Kansas: maize, sorghum, winter_wheat, fallow, cover_crop.
 * - Central Ukraine: maize, winter_wheat, sunflower, soybean, fallow, cover_crop.
 * Any other key in a sequence (perennial_forage, non_arable, other_annual, rapeseed, ...) is a
 * history state of the field's past: shown as "history only; not simulated", never as values.
 */
const BASE_SIMULATED_KEYS = new Set(["maize", "sorghum", "winter_wheat", "fallow", "cover_crop"]);
const REGION_SIMULATED_KEYS: Record<string, ReadonlySet<string>> = {
  ua_central_t36uvu: new Set(["maize", "winter_wheat", "sunflower", "soybean", "fallow", "cover_crop"]),
};

export function isHistoryOnly(key: string, regionId?: string): boolean {
  const keys = (regionId && REGION_SIMULATED_KEYS[regionId]) || BASE_SIMULATED_KEYS;
  return !keys.has(key);
}
