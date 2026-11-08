import type {
  FieldCalendar,
  FieldPack,
  FieldScenarios,
  FieldSeries,
  RegionHindcast,
  RegionIndex,
  RegionLayers,
  RegionList,
} from "./types";

/** True when the app runs on SYNTHETIC demo data (dev server only; a build refuses it). */
export const IS_DEMO_DATA = __FW_DATA_MODE__ === "fixtures";

const base = `${import.meta.env.BASE_URL}packs/`;

/** Static hosts may answer a missing file with index.html and status 200; that is not data. */
const isJson = (res: Response) => res.ok && (res.headers.get("content-type") ?? "").includes("json");

async function get<T>(path: string): Promise<T> {
  const res = await fetch(base + path);
  if (!isJson(res)) {
    throw new Error(res.ok ? `${path} is missing` : `${path} returned HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

/**
 * Data caching: packs are cached on-demand by the service worker when requested,
 * rather than pre-fetching all 800+ files on startup.
 */
export function cacheRegionForOffline(_index: RegionIndex): void {
  // On-demand caching handled by service worker
}

export const loadRegions = () => get<RegionList>("regions.json");
export const loadIndex = (region: string) => get<RegionIndex>(`${region}/index.json`);
export const loadHindcast = (region: string) => get<RegionHindcast>(`${region}/hindcast.json`);
export const loadLayers = (region: string) => get<RegionLayers>(`${region}/layers.json`);
export const loadPack = (region: string, fid: string) => get<FieldPack>(`${region}/${fid}.json`);
export const loadSeries = (region: string, fid: string) =>
  get<FieldSeries>(`${region}/${fid}.series.json`);
export const loadCalendar = (region: string, fid: string) =>
  get<FieldCalendar>(`${region}/${fid}.calendar.json`);
export const loadScenarios = (region: string, fid: string) =>
  get<FieldScenarios>(`${region}/${fid}.scenarios.json`);
