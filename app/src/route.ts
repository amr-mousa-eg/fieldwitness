import { useEffect, useState } from "react";

export type FieldTab = "story" | "options" | "calendar" | "advisor";
export const TABS: FieldTab[] = ["story", "options", "calendar", "advisor"];

/** Region-level pages. Field ids are 40-hex hashes, so these names never collide with one. */
export type RegionPage = "map" | "scoreboard" | "methods";
export const PAGES: RegionPage[] = ["map", "scoreboard", "methods"];

/** App location in the URL hash: #/<region_id>[/<page> | /<field_id>[/<tab>]]. */
export interface Route {
  regionId: string | null;
  page: RegionPage;
  fieldId: string | null;
  tab: FieldTab;
}

export function parseHash(hash: string): Route {
  const [regionId = null, second = null, tab = "story"] = hash
    .replace(/^#\/?/, "")
    .split("/")
    .filter(Boolean)
    .map(decodeURIComponent);
  const page = PAGES.includes(second as RegionPage) ? (second as RegionPage) : "map";
  const fieldId = second !== null && !PAGES.includes(second as RegionPage) ? second : null;
  return { regionId, page, fieldId, tab: TABS.includes(tab as FieldTab) ? (tab as FieldTab) : "story" };
}

export function routeHref(regionId: string, fieldId?: string | null, tab?: FieldTab): string {
  const parts = [regionId, fieldId, fieldId ? tab : null]
    .filter((p): p is string => !!p)
    .map(encodeURIComponent);
  return `#/${parts.join("/")}`;
}

export function pageHref(regionId: string, page: RegionPage): string {
  return page === "map" ? routeHref(regionId) : `#/${encodeURIComponent(regionId)}/${page}`;
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseHash(window.location.hash));
  useEffect(() => {
    const on = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}
