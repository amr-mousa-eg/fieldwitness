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

/** Must match DATA_CACHE in public/sw.js. */
const DATA_CACHE = "fw-data-v1";

/**
 * Production only: store every file of this region in the service worker's data cache, so all
 * of its fields open offline after one visit (T9.1), not only the fields already viewed.
 * Missing files (e.g. a region without layers.json) are skipped.
 */
export function cacheRegionForOffline(index: RegionIndex): void {
  if (!import.meta.env.PROD || !("caches" in window)) return;
  const r = index.region_id;
  const paths = ["regions.json", `${r}/index.json`, `${r}/hindcast.json`, `${r}/layers.json`];
  for (const f of index.fields) {
    for (const part of ["", ".series", ".calendar", ".scenarios"]) paths.push(`${r}/${f.field_id}${part}.json`);
  }
  void caches.open(DATA_CACHE).then((c) =>
    Promise.allSettled(
      paths.map(async (p) => {
        const res = await fetch(base + p);
        if (isJson(res)) await c.put(base + p, res);
      }),
    ),
  );
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
