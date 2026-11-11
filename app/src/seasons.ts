/**
 * Season keys the rotation model simulates: the crops with a sowing day in
 * `src/fieldwitness/rotate/slots.py` (maize, sorghum, winter wheat) plus fallow and cover crop.
 * Any other key in a sequence (perennial_forage, non_arable, other_annual, soybean, ...) is a
 * history state of the field's past: shown as "history only; not simulated", never as values.
 */
const SIMULATED_SEASON_KEYS = new Set(["maize", "sorghum", "winter_wheat", "fallow", "cover_crop"]);

export function isHistoryOnly(key: string): boolean {
  return !SIMULATED_SEASON_KEYS.has(key);
}
